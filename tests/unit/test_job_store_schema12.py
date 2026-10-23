# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Schema 12: the submission claim time, the 11 -> 12 upgrade and explicit links (#494)."""

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from scenario.core.jobs import store as storage
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
    StoreConflict,
    StoreError,
)
from tests.unit.test_job_store_schema10 import _dump, _pragma, _rows, _scopes

# SQL dump of a database written by the schema 11 release's storage code.
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/synthetic/jobs-schema11.sql"
CLAIMED = "2026-10-14T21:18:11.123Z"


def materialize(path):
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(FIXTURE.read_text(encoding="utf-8"))
    return path


@pytest.fixture
def schema11(tmp_path):
    return materialize(tmp_path / "jobs.sqlite3")


@pytest.fixture
def scope():
    return JobScope("https://service.example.invalid/v1", "local-key-one", "project-one")


@pytest.fixture
def store(tmp_path, scope):
    return JobStore(tmp_path / "jobs.sqlite3", scope)


def _intent(scope, request_id="request", operation="model", target_id="model_target"):
    return JobIntent(
        request_id,
        scope,
        JobOrigin("file", "scene", "revision", "target"),
        operation,
        target_id,
        "a" * 64,
        "b" * 64,
        "1.5",
    )


def _uncertain(store, request_id="request", **changes):
    record = store.create(_intent(store.scope, request_id, **changes))
    record = store.transition(
        request_id,
        expected_revision=record.revision,
        state=JobState.SUBMITTING,
        claimed_at=CLAIMED,
    )
    return store.transition(request_id, expected_revision=record.revision, state=JobState.UNCERTAIN)


def _upgraded(raw):
    """A schema 11 row as the upgrade rewrites it: unknown claim time, parents and lane."""
    expected = json.loads(raw) | {"claimed_at": None}
    if expected["intent"].get("source") != "cloud":
        expected["intent"]["lane"] = None
    for item in expected["results"]:
        item["asset"]["parent_id"] = None
    return expected


def _succeeded(store, request_id="request"):
    record = store.create(_intent(store.scope, request_id))
    for state, changes in (
        (JobState.SUBMITTING, {"claimed_at": CLAIMED}),
        (JobState.REMOTE, {"remote_job_id": f"remote-{request_id}"}),
        (JobState.SUCCEEDED, {}),
    ):
        record = store.transition(
            request_id, expected_revision=record.revision, state=state, **changes
        )
    return record


def _package(**parents):
    """A GLB, an OBJ and an MTL; keyword arguments name each file's parent."""
    return tuple(
        ResultAsset(
            asset_id, f"{index:03d}-{asset_id}.bin", media_type, parent_id=parents.get(asset_id)
        )
        for index, (asset_id, media_type) in enumerate(
            (("glb", "model/gltf-binary"), ("obj", "model/obj"), ("mtl", "model/mtl"))
        )
    )


def test_fixture_is_the_unmodified_schema_eleven_store(schema11):
    assert _pragma(schema11, "user_version") == 11
    assert _pragma(schema11, "application_id") == storage._APPLICATION_ID
    assert len(_rows(schema11, "jobs", "scope, request_id, revision")) == 17
    assert len(_rows(schema11, "trained_defaults", "scope, lane, revision")) == 1
    assert len(_scopes(schema11)) == 2
    for *_, raw in _rows(schema11, "jobs", "scope, request_id, revision, record"):
        assert "claimed_at" not in json.loads(raw)


def test_real_schema_eleven_store_upgrades_every_row_with_an_unknown_claim_time(schema11):
    before = _rows(schema11, "jobs", "scope, request_id, revision, record")
    uploads = _rows(schema11, "film_uploads", "scope, production_id, task_id, record")
    defaults = _rows(schema11, "trained_defaults", "scope, lane, revision, record")
    stores = {key: JobStore(schema11, scope) for key, scope in _scopes(schema11).items()}
    assert _pragma(schema11, "user_version") == storage._VERSION
    after = _rows(schema11, "jobs", "scope, request_id, revision, record")
    assert [row[:3] for row in after] == [row[:3] for row in before]
    for (key, request_id, _, raw), (*_, migrated) in zip(before, after, strict=True):
        expected = _upgraded(raw)
        assert json.loads(migrated) == expected
        record = stores[key].get(request_id)
        assert record.claimed_at is None
        assert json.loads(json.dumps(asdict(record))) == expected
    assert _rows(schema11, "film_uploads", "scope, production_id, task_id, record") == uploads
    assert _rows(schema11, "trained_defaults", "scope, lane, revision, record") == defaults
    selected = next(store for store in stores.values() if store.scope.project_id)
    assert selected.get("p-uncertain-model").state == JobState.UNCERTAIN
    assert selected.get("b-uncertain").state == JobState.UNCERTAIN
    assert {item.asset.source for item in selected.get("o-originals").results} == {"original"}
    assert selected.trained_default("image").default.picks[0].scale == 0.75
    migrated = _dump(schema11)
    JobStore(schema11, selected.scope)
    assert _dump(schema11) == migrated


@pytest.mark.parametrize("damage", ["job-record", "default-record"])
def test_failed_schema_eleven_upgrade_preserves_every_byte(schema11, damage):
    scope = next(iter(_scopes(schema11).values()))
    with sqlite3.connect(schema11) as connection:
        if damage == "job-record":
            connection.execute("UPDATE jobs SET record='{}' WHERE request_id='p-uncertain-model'")
        else:
            connection.execute("UPDATE trained_defaults SET record='{}'")
    before = schema11.read_bytes()
    with pytest.raises(StoreError):
        JobStore(schema11, scope)
    assert schema11.read_bytes() == before
    assert _pragma(schema11, "user_version") == 11


def test_schema_eleven_row_that_already_names_a_claim_time_is_refused(schema11):
    scope = next(iter(_scopes(schema11).values()))
    with sqlite3.connect(schema11) as connection:
        (raw,) = connection.execute(
            "SELECT record FROM jobs WHERE request_id='p-uncertain-model'"
        ).fetchone()
        value = json.loads(raw) | {"claimed_at": CLAIMED}
        connection.execute(
            "UPDATE jobs SET record=? WHERE request_id='p-uncertain-model'", (json.dumps(value),)
        )
    before = schema11.read_bytes()
    with pytest.raises(StoreError):
        JobStore(schema11, scope)
    assert schema11.read_bytes() == before


def test_schema_twelve_is_refused_by_a_schema_eleven_reader_and_newer_by_this_one(
    schema11, monkeypatch
):
    scope = next(iter(_scopes(schema11).values()))
    JobStore(schema11, scope)
    upgraded = schema11.read_bytes()
    with monkeypatch.context() as patch:
        # The schema 11 release refuses the store as a newer format, not as damage.
        patch.setattr(storage, "_VERSION", 11)
        with pytest.raises(StoreError, match="Unsupported"):
            JobStore(schema11, scope)
    assert schema11.read_bytes() == upgraded
    with sqlite3.connect(schema11) as connection:
        connection.execute(f"PRAGMA user_version={storage._VERSION + 1}")
    newer = schema11.read_bytes()
    with pytest.raises(StoreError, match="Unsupported"):
        JobStore(schema11, scope)
    assert schema11.read_bytes() == newer


def test_claim_time_is_saved_with_the_submitting_claim_and_kept(store):
    record = store.create(_intent(store.scope))
    assert record.claimed_at is None
    record = store.transition(
        "request", expected_revision=0, state=JobState.SUBMITTING, claimed_at=CLAIMED
    )
    assert record.claimed_at == CLAIMED
    record = store.transition(
        "request", expected_revision=record.revision, state=JobState.REMOTE, remote_job_id="job"
    )
    record = store.transition("request", expected_revision=record.revision, state=JobState.FAILED)
    assert store.get("request").claimed_at == CLAIMED == record.claimed_at


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-14T21:18:11Z",
        "2026-10-14 21:18:11.123Z",
        "2026-10-14T21:18:11.123+00:00",
        "2026-13-14T21:18:11.123Z",
        "",
        1760476691.123,
    ],
)
def test_claim_time_is_an_exact_utc_millisecond_timestamp(store, value):
    store.create(_intent(store.scope))
    with pytest.raises(ValueError):
        store.transition(
            "request", expected_revision=0, state=JobState.SUBMITTING, claimed_at=value
        )
    assert store.get("request").state == JobState.PREPARED


def test_claim_time_is_only_saved_by_the_submitting_claim(store):
    record = _uncertain(store)
    with pytest.raises(ValueError):
        store.transition(
            "request",
            expected_revision=record.revision,
            state=JobState.REMOTE,
            remote_job_id="job",
            claimed_at=CLAIMED,
        )
    store.create(_intent(store.scope, "other"))
    with pytest.raises(ValueError):
        store.transition("other", expected_revision=0, state=JobState.CANCELED, claimed_at=CLAIMED)


def test_claim_time_on_a_prepared_or_cloud_row_is_invalid_data(store):
    record = store.create(_intent(store.scope))
    with sqlite3.connect(store._path) as connection:
        value = asdict(replace(record, claimed_at=CLAIMED))
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    with pytest.raises(StoreError):
        store.get("request")


def test_claim_time_helpers_round_trip_service_timestamps():
    text = storage.claim_time(1760476691.1234)
    assert text == "2025-10-14T21:18:11.123Z"
    parsed = storage.parse_time(text)
    assert parsed.timestamp() == pytest.approx(1760476691.123)
    assert storage.parse_time("2023-02-03T11:19:41.579Z").year == 2023
    for value in (None, "", "yesterday", 3, "2023-02-03T11:19:41"):
        assert storage.parse_time(value) is None


def test_link_binds_a_selected_remote_job_to_an_unconfirmed_request(store):
    record = _uncertain(store)
    linked = store.link_remote("request", expected_revision=record.revision, remote_job_id="job")
    assert (linked.state, linked.remote_job_id, linked.revision) == (
        JobState.REMOTE,
        "job",
        record.revision + 1,
    )
    assert linked.claimed_at == CLAIMED
    assert store.get("request") == linked
    assert store.remote_job_ids() == frozenset({"job"})


def test_link_accepts_a_submitting_request_left_by_an_earlier_session(store):
    store.create(_intent(store.scope))
    record = store.transition(
        "request", expected_revision=0, state=JobState.SUBMITTING, claimed_at=CLAIMED
    )
    linked = store.link_remote("request", expected_revision=record.revision, remote_job_id="job")
    assert linked.state == JobState.REMOTE


def test_link_refuses_a_remote_job_already_saved_in_this_scope(store, tmp_path):
    _uncertain(store, "first")
    record = _uncertain(store, "second")
    store.link_remote("first", expected_revision=store.get("first").revision, remote_job_id="job")
    before = store.get("second")
    with pytest.raises(StoreConflict, match="already saved"):
        store.link_remote("second", expected_revision=record.revision, remote_job_id="job")
    assert store.get("second") == before
    # Another credential scope may hold the same remote ID without conflict.
    other = JobStore(tmp_path / "jobs.sqlite3", replace(store.scope, account_id="other-key"))
    third = _uncertain(other, "third")
    assert (
        other.link_remote("third", expected_revision=third.revision, remote_job_id="job").state
        == JobState.REMOTE
    )


def test_link_refuses_a_stale_revision_or_a_confirmed_request(store):
    record = _uncertain(store)
    with pytest.raises(StoreConflict):
        store.link_remote("request", expected_revision=record.revision - 1, remote_job_id="job")
    store.link_remote("request", expected_revision=record.revision, remote_job_id="job")
    with pytest.raises(StoreConflict):
        store.link_remote(
            "request", expected_revision=store.get("request").revision, remote_job_id="other"
        )
    store.create(_intent(store.scope, "prepared"))
    with pytest.raises(StoreConflict):
        store.link_remote("prepared", expected_revision=0, remote_job_id="other")
    with pytest.raises(StoreConflict):
        store.link_remote("missing", expected_revision=0, remote_job_id="other")
    with pytest.raises(ValueError):
        store.link_remote("prepared", expected_revision=0, remote_job_id="bad/id")


def test_result_parent_round_trips_within_the_manifest(store):
    record = _succeeded(store)
    store.set_results("request", _package(obj="glb", mtl="glb"), expected_revision=record.revision)
    parents = [item.asset.parent_id for item in store.get("request").results]
    assert parents == [None, "glb", "glb"]


@pytest.mark.parametrize("parent", ["obj", "", "bad/id", "has space"])
def test_result_parent_must_be_another_opaque_identity(parent):
    with pytest.raises(ValueError):
        ResultAsset("obj", "001-obj.bin", "model/obj", parent_id=parent)


@pytest.mark.parametrize(
    "parents",
    [
        {"obj": "elsewhere"},
        {"obj": "mtl", "mtl": "obj"},
        {"glb": "obj", "obj": "mtl", "mtl": "glb"},
    ],
)
def test_result_parent_outside_the_manifest_or_on_a_cycle_is_refused(store, parents):
    record = _succeeded(store)
    with pytest.raises(ValueError):
        store.set_results("request", _package(**parents), expected_revision=record.revision)
    assert store.get("request").results == ()


def test_schema_twelve_row_without_a_result_parent_is_invalid_data(store, tmp_path):
    record = _succeeded(store)
    store.set_results("request", _package(), expected_revision=record.revision)
    with closing(sqlite3.connect(tmp_path / "jobs.sqlite3")) as connection, connection:
        (raw,) = connection.execute("SELECT record FROM jobs").fetchone()
        value = json.loads(raw)
        del value["results"][0]["asset"]["parent_id"]
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    with pytest.raises(StoreError):
        store.get("request")
