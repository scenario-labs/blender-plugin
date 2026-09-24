# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Durable application admission and receipts, without Blender or network activity."""

import gc
import hashlib
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import (
    ApplicationClaim,
    ApplicationError,
    JobCoordinator,
    RecoveryAction,
)
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import (
    JobIntent,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.transfers import DownloadedResult, ResultDownloader, StoragePolicy

DATA = b"locally verified application bytes"
SCOPE = JobScope("https://service.example.invalid/v1", "account", "project", "team")


@pytest.fixture
def env(tmp_path):
    origins = OriginRevisions()
    origin = origins.capture("scene", "target")
    store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    record = store.create(
        JobIntent("request", SCOPE, origin, "model", "model", "a" * 64, "b" * 64, "1.0")
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        record = store.transition(
            "request",
            expected_revision=record.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    digest = hashlib.sha256(DATA).hexdigest()
    asset = ResultAsset("asset", "result.png", "image/png", len(DATA), digest)
    record = store.set_results("request", (asset,), expected_revision=record.revision)
    record = store.transition(
        "request", expected_revision=record.revision, state=JobState.DOWNLOADING
    )
    receipt = DownloadedResult(asset.name, len(DATA), digest)
    record = store.record_download("request", "asset", receipt, expected_revision=record.revision)
    ready = store.transition("request", expected_revision=record.revision, state=JobState.READY)
    root = tmp_path / "results"
    root.mkdir()
    owners = []
    requests = []

    def deny(request):
        requests.append(request)
        pytest.fail("Application admission/receipts must never contact a service")

    def owner(*, scope=SCOPE, guard=origins.guard):
        adapter = SDKAdapter(
            Credentials("fixture-key", "fixture-secret"),
            base_url=scope.service,
            account_id=scope.account_id,
            project_id=scope.project_id,
            team_id=scope.team_id,
            online=lambda: False,
            transport=httpx.MockTransport(deny),
        )
        coordinator = JobCoordinator(
            adapter,
            JobStore(tmp_path / "jobs.sqlite3", scope),
            origin_guard=guard,
            result_root=root,
            result_downloader=ResultDownloader(
                StoragePolicy(frozenset({"storage.example.invalid"})),
                online_access=lambda: False,
            ),
        )
        owners.append(coordinator)
        return coordinator

    coordinator = owner()
    # Materialize the same private scope/request layout used by result commands.
    # No transport runs: this fixture represents a previously downloaded receipt.
    from dataclasses import asdict

    from scenario.core.jobs.store import _json

    directory = root / hashlib.sha256(_json(asdict(SCOPE)).encode()).hexdigest()
    directory /= hashlib.sha256(b"request").hexdigest()
    directory.mkdir(parents=True)
    path = directory / receipt.name
    path.write_bytes(DATA)
    yield SimpleNamespace(
        coordinator=coordinator,
        store=store,
        ready=ready,
        owner=owner,
        origins=origins,
        path=path,
        requests=requests,
    )
    for coordinator in owners:
        coordinator.close()
    assert requests == []


def verified(env, owner=None, record=None):
    return (owner or env.coordinator).verify_results(
        "request", expected_revision=(record or env.ready).revision
    )


def test_claim_precedes_application_and_completion_is_once_only(env):
    ticket = verified(env)
    claim = env.coordinator.claim_application(ticket)
    assert isinstance(claim, ApplicationClaim)
    assert env.store.get("request") == claim.record
    assert claim.record.state == JobState.APPLYING
    assert claim.record.intent == env.ready.intent
    assert claim.paths == (env.path,)
    with pytest.raises(FrozenInstanceError):
        claim.paths = ()
    applied = env.coordinator.complete_application(claim)
    assert applied.state == JobState.APPLIED
    assert applied.results == env.ready.results
    assert env.store.get("request") == applied
    for finish in (env.coordinator.complete_application, env.coordinator.fail_application):
        with pytest.raises(ApplicationError):
            finish(claim)
    assert env.store.get("request") == applied


@pytest.mark.parametrize("kind", ["none", "copy", "paths", "record", "foreign-owner"])
def test_fabricated_or_foreign_verification_cannot_claim(env, kind):
    ticket = verified(env)
    rejected = {
        "none": None,
        "copy": replace(ticket),
        "paths": replace(ticket, paths=(env.path.parent / "unverified.png",)),
        "record": replace(ticket, record=replace(ticket.record, revision=999)),
        "foreign-owner": verified(env, env.owner()),
    }[kind]
    with pytest.raises(ApplicationError):
        env.coordinator.claim_application(rejected)
    assert env.store.get("request") == env.ready


@pytest.mark.parametrize("component", ["service", "account_id", "project_id", "team_id"])
def test_other_scope_cannot_claim_or_finish_original_ticket(env, component):
    ticket = verified(env)
    changed = "https://other.example.invalid/v1" if component == "service" else "other"
    foreign = env.owner(scope=replace(SCOPE, **{component: changed}))
    with pytest.raises(ApplicationError):
        foreign.claim_application(ticket)
    claim = env.coordinator.claim_application(ticket)
    with pytest.raises(ApplicationError):
        foreign.complete_application(claim)
    assert env.store.get("request") == claim.record


@pytest.mark.parametrize("change", ["invalidate", "reset", "deactivate", "missing-guard"])
def test_origin_and_owner_are_rechecked_at_claim(env, change):
    owner = env.owner(guard=None) if change == "missing-guard" else env.coordinator
    ticket = verified(env, owner)
    if change == "invalidate":
        env.origins.invalidate("scene")
    elif change == "reset":
        env.origins.reset()
    elif change == "deactivate":
        owner.deactivate()
    with pytest.raises(ApplicationError):
        owner.claim_application(ticket)
    assert env.store.get("request") == env.ready


def test_changed_receipt_file_cannot_issue_verification(env):
    env.path.write_bytes(b"changed bytes")
    with pytest.raises(ResultError):
        verified(env)
    assert env.store.get("request") == env.ready


def test_confirmation_after_invalidation_and_deactivation_stays_in_original_scope(env):
    claim = env.coordinator.claim_application(verified(env))
    env.origins.invalidate("scene")
    env.coordinator.close()
    applied = env.coordinator.complete_application(claim)
    assert applied.state == JobState.APPLIED
    assert applied.intent == env.ready.intent
    assert env.store.get("request") == applied


def test_confirmed_rollback_requires_fresh_verification_to_retry(env):
    ticket = verified(env)
    claim = env.coordinator.claim_application(ticket)
    failed = env.coordinator.fail_application(claim)
    assert failed.state == JobState.APPLY_FAILED
    with pytest.raises(ApplicationError):
        env.coordinator.claim_application(ticket)
    claim = env.coordinator.claim_application(verified(env, record=failed))
    assert claim.record.revision == failed.revision + 1
    assert env.coordinator.complete_application(claim).state == JobState.APPLIED


def test_failed_application_with_changed_origin_cannot_be_rebound(env):
    claim = env.coordinator.claim_application(verified(env))
    failed = env.coordinator.fail_application(claim)
    env.origins.invalidate("scene")
    env.origins.capture("scene", "target")
    ticket = verified(env, record=failed)
    with pytest.raises(ApplicationError):
        env.coordinator.claim_application(ticket)
    assert env.store.get("request") == failed


@pytest.mark.parametrize("finish", [False, True])
def test_recovery_preserves_interrupted_or_completed_application_without_replay(env, finish):
    claim = env.coordinator.claim_application(verified(env))
    record = env.coordinator.complete_application(claim) if finish else claim.record
    restarted = env.owner(guard=OriginRevisions().guard)
    assert restarted.recovery_plan()[0].record == record
    assert restarted.recovery_plan()[0].action == (
        RecoveryAction.FINISHED if finish else RecoveryAction.REVIEW_APPLICATION
    )
    with pytest.raises(ApplicationError):
        restarted.complete_application(claim)
    if finish:
        ticket = verified(env, restarted, record)
        with pytest.raises(ApplicationError):
            restarted.claim_application(ticket)
    else:
        with pytest.raises(StoreConflict):
            verified(env, restarted, record)
    assert env.store.get("request") == record


@pytest.mark.parametrize("error_type", [StoreError, KeyboardInterrupt])
@pytest.mark.parametrize("after_commit", [False, True])
def test_claim_write_failure_or_interruption_never_returns_authorization(
    env, monkeypatch, error_type, after_commit
):
    ticket = verified(env)
    transition = env.coordinator._store.transition

    def fail(*args, **kwargs):
        if after_commit:
            transition(*args, **kwargs)
        raise error_type("synthetic persistence interruption")

    monkeypatch.setattr(env.coordinator._store, "transition", fail)
    with pytest.raises(error_type):
        env.coordinator.claim_application(ticket)
    with pytest.raises(ApplicationError):
        env.coordinator.claim_application(ticket)
    assert env.store.get("request").state == (JobState.APPLYING if after_commit else JobState.READY)
    assert not env.coordinator._application_claims


@pytest.mark.parametrize("method", ["complete_application", "fail_application"])
@pytest.mark.parametrize("error_type", [StoreError, KeyboardInterrupt])
@pytest.mark.parametrize("after_commit", [False, True])
def test_receipt_write_failure_preserves_evidence_without_repeating_application(
    env, monkeypatch, method, error_type, after_commit
):
    claim = env.coordinator.claim_application(verified(env))
    transition = env.coordinator._store.transition

    def fail(*args, **kwargs):
        if after_commit:
            transition(*args, **kwargs)
        raise error_type("synthetic receipt persistence interruption")

    monkeypatch.setattr(env.coordinator._store, "transition", fail)
    with pytest.raises(error_type):
        getattr(env.coordinator, method)(claim)
    expected = JobState.APPLIED if method == "complete_application" else JobState.APPLY_FAILED
    assert env.store.get("request").state == (expected if after_commit else JobState.APPLYING)
    monkeypatch.setattr(env.coordinator._store, "transition", transition)
    if after_commit:
        with pytest.raises(StoreConflict):
            getattr(env.coordinator, method)(claim)
    else:
        # Retrying a failed local receipt write does not perform Blender work.
        saved = getattr(env.coordinator, method)(claim)
        assert saved.state == expected


def test_competing_owners_can_commit_only_one_application_claim(env):
    owners = env.coordinator, env.owner()
    tickets = tuple(verified(env, owner) for owner in owners)
    barrier = threading.Barrier(2)

    def claim(pair):
        owner, ticket = pair
        barrier.wait(timeout=5)
        try:
            return owner.claim_application(ticket)
        except StoreConflict as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(claim, zip(owners, tickets, strict=True)))
    claims = [result for result in outcomes if isinstance(result, ApplicationClaim)]
    assert len(claims) == 1
    assert sum(isinstance(result, StoreConflict) for result in outcomes) == 1
    assert env.store.get("request") == claims[0].record


def test_origin_invalidation_waits_through_durable_claim_then_can_proceed(env, monkeypatch):
    ticket = verified(env)
    entered, release, attempted, invalidated = (threading.Event() for _ in range(4))
    transition = env.coordinator._store.transition

    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return transition(*args, **kwargs)

    def invalidate():
        attempted.set()
        env.origins.invalidate("scene")
        invalidated.set()

    monkeypatch.setattr(env.coordinator._store, "transition", blocked)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(env.coordinator.claim_application, ticket)
        assert entered.wait(5)
        changed = pool.submit(invalidate)
        assert attempted.wait(5)
        assert not invalidated.wait(0.05)
        release.set()
        claim = pending.result(5)
        changed.result(5)
    assert invalidated.is_set()
    assert env.store.get("request") == claim.record
    assert env.coordinator.complete_application(claim).state == JobState.APPLIED


def test_unused_tickets_and_claims_are_not_kept_alive_by_owner(env):
    ticket = verified(env)
    reference = weakref.ref(ticket)
    del ticket
    gc.collect()
    assert reference() is None
    claim = env.coordinator.claim_application(verified(env))
    reference = weakref.ref(claim)
    del claim
    gc.collect()
    assert reference() is None
    assert env.coordinator.recovery_plan()[0].record.state == JobState.APPLYING


def test_copied_or_stale_claim_cannot_report_application_outcome(env):
    claim = env.coordinator.claim_application(verified(env))
    for invalid in (None, replace(claim), replace(claim, paths=())):
        with pytest.raises(ApplicationError):
            env.coordinator.complete_application(invalid)
    changed = env.store.transition(
        "request", expected_revision=claim.record.revision, state=JobState.APPLY_FAILED
    )
    with pytest.raises(StoreConflict):
        env.coordinator.complete_application(claim)
    assert env.store.get("request") == changed


def test_retirement_during_verification_does_not_issue_a_late_application_ticket(env, monkeypatch):
    verify = env.coordinator._results.verify_ready

    def late(*args, **kwargs):
        result = verify(*args, **kwargs)
        env.coordinator.deactivate()
        return result

    monkeypatch.setattr(env.coordinator._results, "verify_ready", late)
    with pytest.raises(ResultError, match="inactive"):
        verified(env)
    assert not env.coordinator._verified_results
    assert env.store.get("request") == env.ready
