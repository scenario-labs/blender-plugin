# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit per-scope trained-model lane defaults through their owner, offline."""

import json
import os
import shutil
import sqlite3
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, replace
from threading import Barrier
from types import SimpleNamespace

import pytest

from scenario.core.api.sdk_adapter import Credentials
from scenario.core.jobs.credential_storage import open_credential_store
from scenario.core.jobs.model_defaults import (
    DefaultsRetired,
    ModelDefaults,
    describe,
    parse_default,
)
from scenario.core.jobs.store import (
    JobScope,
    JobStore,
    StoreConflict,
    StoreError,
    TrainedDefaultState,
    TrainedModelDefault,
    TrainedModelPick,
)

KEY = Credentials("fixture-key", "fixture-secret")


def stack(lane="image", model_id="model_lora", scale=0.8):
    return TrainedModelDefault(lane, "stack", "model_base", (TrainedModelPick(model_id, scale),))


def owner_for(root, credentials=KEY, **scope):
    return ModelDefaults(open_credential_store(root, credentials, **scope))


@pytest.fixture
def root(tmp_path):
    return tmp_path / "shared-jobs"


@pytest.fixture
def owner(root):
    return owner_for(root)


def database(root):
    return root / "jobs.sqlite3"


def test_owner_serves_exactly_the_store_scope_it_was_given(root):
    store = open_credential_store(root, KEY, project_id="project-a")
    owner = ModelDefaults(store)
    assert owner.scope == store.scope
    assert owner.scope.project_id == "project-a"
    assert owner.active
    assert len(owner.context_id) == 32
    assert ModelDefaults(store).context_id != owner.context_id
    for invalid in (None, {"scope": store.scope}, SimpleNamespace(scope=store.scope)):
        with pytest.raises(ValueError, match="credential-bound job store"):
            ModelDefaults(invalid)


def test_reading_unsaved_lanes_never_writes_or_falls_back(owner, root):
    owner.save(stack("render_image"), expected_revision=0)
    before = database(root).read_bytes()
    for lane in ("image", "video", "3d"):
        assert owner.lane(lane) == TrainedDefaultState(lane, 0)
    assert owner.saved() == (TrainedDefaultState("render_image", 1, stack("render_image")),)
    assert database(root).read_bytes() == before


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ({}, {"project_id": "project-a"}),
        ({"project_id": "project-a"}, {}),
        ({"project_id": "project-a"}, {"project_id": "project-b"}),
        ({"project_id": "project-a"}, {"project_id": "project-a", "team_id": "team-a"}),
        ({}, {"credentials": Credentials("other-key", "fixture-secret")}),
        ({}, {"credentials": Credentials("fixture-key", "other-secret")}),
    ],
)
def test_defaults_never_cross_credentials_projects_or_teams(root, first, second):
    """A key-scope default is not a project default, and no scope inherits another's."""
    saved_owner = owner_for(root, **first)
    saved = saved_owner.save(stack(), expected_revision=0)
    other = owner_for(root, **second)
    assert other.scope != saved_owner.scope
    assert other.lane("image") == TrainedDefaultState("image", 0)
    assert other.saved() == ()
    with pytest.raises(StoreConflict):
        other.clear("image", expected_revision=1)
    own = other.save(stack(model_id="model_other"), expected_revision=0)
    assert owner_for(root, **first).lane("image") == saved
    assert owner_for(root, **second).lane("image") == own


def test_blank_project_selects_the_key_scope_not_a_discovered_project(root):
    """The owner takes the explicit override only; no project is inferred for a key."""
    owner = owner_for(root, project_id=None)
    assert (owner.scope.project_id, owner.scope.team_id) == (None, None)
    saved = owner.save(stack(), expected_revision=0)
    assert owner_for(root).lane("image") == saved


def test_writes_require_an_explicit_default_and_the_observed_revision(owner, root):
    saved = owner.save(stack(), expected_revision=0)
    for value in (describe(saved)["default"], {"lane": "image"}, None, "model_base"):
        with pytest.raises(ValueError, match="explicit trained-model default"):
            owner.save(value, expected_revision=1)
    for revision in (None, "1", 1.0, -1, True):
        with pytest.raises(ValueError, match="expected revision"):
            owner.save(stack(model_id="model_new"), expected_revision=revision)
    with pytest.raises(TypeError):
        owner.save(stack(), 1)
    with pytest.raises(TypeError):
        owner.clear("image", 1)
    with pytest.raises(StoreConflict):
        owner.save(stack(model_id="model_new"), expected_revision=0)
    assert owner.lane("image") == saved
    cleared = owner.clear("image", expected_revision=1)
    assert cleared == TrainedDefaultState("image", 2)
    with pytest.raises(StoreConflict):
        owner.save(stack(), expected_revision=1)
    assert owner.save(stack(), expected_revision=2).revision == 3


def test_two_owners_of_one_scope_cannot_both_win(root):
    first, second = owner_for(root), owner_for(root)
    barrier = Barrier(2)

    def save(item):
        target, model_id = item
        barrier.wait()
        try:
            return target.save(stack(model_id=model_id), expected_revision=0)
        except StoreConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(save, [(first, "model_first"), (second, "model_second")]))
    winners = [outcome for outcome in outcomes if outcome is not None]
    assert len(winners) == 1
    assert first.lane("image") == second.lane("image") == winners[0]


def test_retired_owner_refuses_every_call_without_touching_storage(owner, root):
    saved = owner.save(stack(), expected_revision=0)
    before = database(root).read_bytes()
    owner.retire()
    owner.retire()
    assert not owner.active
    calls = (
        lambda: owner.lane("image"),
        owner.saved,
        lambda: owner.save(stack(model_id="model_late"), expected_revision=1),
        lambda: owner.clear("image", expected_revision=1),
    )
    for call in calls:
        with pytest.raises(DefaultsRetired, match="credentials or project changed"):
            call()
    assert issubclass(DefaultsRetired, StoreConflict)
    assert database(root).read_bytes() == before
    assert owner_for(root).lane("image") == saved


def test_retire_waits_for_a_running_write(owner, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = JobStore.set_trained_default

    def slow(store, default, *, expected_revision):
        entered.set()
        assert release.wait(5)
        return original(store, default, expected_revision=expected_revision)

    monkeypatch.setattr(JobStore, "set_trained_default", slow)
    results = []
    writer = threading.Thread(
        target=lambda: results.append(owner.save(stack(), expected_revision=0))
    )
    writer.start()
    assert entered.wait(5)
    retiring = threading.Thread(target=owner.retire)
    retiring.start()
    retiring.join(0.2)
    assert retiring.is_alive() and owner.active
    release.set()
    writer.join(5)
    retiring.join(5)
    assert results == [TrainedDefaultState("image", 1, stack())]
    assert not owner.active
    with pytest.raises(DefaultsRetired):
        owner.lane("image")


@pytest.mark.parametrize("damage", ["record", "version"])
def test_damaged_storage_fails_visibly_and_is_preserved(owner, root, damage):
    owner.save(stack(), expected_revision=0)
    with closing(sqlite3.connect(database(root))) as connection, connection:
        if damage == "record":
            connection.execute("UPDATE trained_defaults SET record='{}'")
        else:
            connection.execute("PRAGMA user_version = 11")
    damaged = database(root).read_bytes()
    message = "trained-model default" if damage == "record" else "Unsupported job database"
    for call in (
        lambda: owner.lane("image"),
        owner.saved,
        lambda: owner.save(stack(model_id="model_new"), expected_revision=1),
        lambda: owner.clear("image", expected_revision=1),
    ):
        with pytest.raises(StoreError, match=message):
            call()
    assert database(root).read_bytes() == damaged
    assert owner.active


def test_a_replaced_database_link_is_refused(owner, root, tmp_path):
    owner.save(stack(), expected_revision=0)
    copy = tmp_path / "copy.sqlite3"
    shutil.copyfile(database(root), copy)
    database(root).unlink()
    try:
        os.symlink(copy, database(root))
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are unavailable on this platform")
    with pytest.raises(StoreError, match="regular local file"):
        owner.lane("image")
    with pytest.raises(StoreError, match="regular local file"):
        owner.save(stack(model_id="model_new"), expected_revision=1)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_defaults_add_no_files_beyond_the_private_job_store(owner, root):
    owner.save(stack(), expected_revision=0)
    owner.clear("image", expected_revision=1)
    assert sorted(path.name for path in root.iterdir()) == [
        ".scope.lock",
        "jobs.sqlite3",
        "scope.key",
    ]
    assert stat.S_IMODE(root.stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(database(root).stat().st_mode) & 0o077 == 0


@pytest.mark.parametrize(
    ("lane", "value", "expected"),
    [
        (
            "image",
            {
                "route": "stack",
                "base_model_id": "model_base",
                "picks": [
                    {"model_id": "model_one", "scale": 1},
                    {"model_id": "model_two", "scale": 0.25},
                    {"model_id": "model_three", "scale": None},
                    {"model_id": "model_four"},
                ],
            },
            TrainedModelDefault(
                "image",
                "stack",
                "model_base",
                (
                    TrainedModelPick("model_one", 1.0),
                    TrainedModelPick("model_two", 0.25),
                    TrainedModelPick("model_three"),
                    TrainedModelPick("model_four"),
                ),
            ),
        ),
        (
            "render_image",
            {
                "route": "composition",
                "base_model_id": "model_base",
                "picks": [{"model_id": "model_composition"}],
            },
            TrainedModelDefault(
                "render_image",
                "composition",
                "model_base",
                (TrainedModelPick("model_composition"),),
            ),
        ),
        (
            "3d",
            {"route": "custom", "base_model_id": "model_private", "picks": []},
            TrainedModelDefault("3d", "custom", "model_private"),
        ),
        (
            "video",
            {"route": "direct", "base_model_id": "model_trained", "picks": ()},
            TrainedModelDefault("video", "direct", "model_trained"),
        ),
    ],
)
def test_json_defaults_round_trip_through_describe(owner, lane, value, expected):
    default = parse_default(lane, value)
    assert default == expected
    assert all(type(pick.scale) in {float, type(None)} for pick in default.picks)
    state = owner.save(default, expected_revision=0)
    described = describe(state)
    assert json.loads(json.dumps(described)) == described
    assert set(described) == {"lane", "revision", "default"}
    assert (described["lane"], described["revision"]) == (lane, 1)
    assert parse_default(lane, described["default"]) == default
    assert describe(owner.clear(lane, expected_revision=1)) == {
        "lane": lane,
        "revision": 2,
        "default": None,
    }


def test_described_state_names_no_scope_or_credential_identity(owner):
    described = json.dumps(describe(owner.save(stack(), expected_revision=0)))
    for private in (owner.scope.account_id, owner.scope.service, "fixture-key", "fixture-secret"):
        assert private not in described


VALID = {"route": "stack", "base_model_id": "model_base", "picks": [{"model_id": "model_one"}]}


@pytest.mark.parametrize(
    ("lane", "value"),
    [
        ("image", None),
        ("image", [VALID]),
        ("image", {**VALID, "lane": "image"}),
        ("image", {**VALID, "scope": {}}),
        ("image", {key: VALID[key] for key in ("route", "base_model_id")}),
        ("image", {**VALID, "picks": {"model_id": "model_one"}}),
        ("image", {**VALID, "picks": "model_one"}),
        ("image", {**VALID, "picks": ["model_one"]}),
        ("image", {**VALID, "picks": [{"scale": 0.5}]}),
        ("image", {**VALID, "picks": [{"model_id": "model_one", "weight": 0.5}]}),
        ("image", {**VALID, "picks": [{"model_id": "model_one", "scale": True}]}),
        ("image", {**VALID, "picks": [{"model_id": "model_one", "scale": "0.5"}]}),
        ("image", {**VALID, "picks": [{"model_id": "model_one", "scale": float("nan")}]}),
        ("image", {**VALID, "picks": [{"model_id": "model_one", "scale": float("inf")}]}),
        ("image", {**VALID, "picks": [{"model_id": "model_one", "scale": 10**400}]}),
        ("image", {**VALID, "picks": [{"model_id": f"model_{n}"} for n in range(17)]}),
        ("image", {**VALID, "picks": [{"model_id": "model_one"}, {"model_id": "model_one"}]}),
        ("image", {**VALID, "picks": [{"model_id": "model_base"}]}),
        ("image", {**VALID, "picks": []}),
        ("image", {**VALID, "route": "custom"}),
        ("image", {**VALID, "route": "train"}),
        ("image", {**VALID, "route": "composition", "picks": [{"model_id": "m", "scale": 1}]}),
        ("image", {**VALID, "base_model_id": "https://private.invalid/model"}),
        ("image", {**VALID, "picks": [{"model_id": "model?token=secret"}]}),
        ("Image", VALID),
        ("../image", VALID),
        (None, VALID),
    ],
)
def test_invalid_json_defaults_are_refused_before_storage(lane, value):
    with pytest.raises(ValueError):
        parse_default(lane, value)


def test_describe_requires_a_saved_lane_state(owner):
    assert describe(owner.lane("image")) == {"lane": "image", "revision": 0, "default": None}
    for invalid in (None, stack(), {"lane": "image", "revision": 0, "default": None}):
        with pytest.raises(ValueError, match="saved lane state"):
            describe(invalid)


def test_owner_scope_matches_the_job_scope_hash_used_by_jobs(root):
    """Defaults share the jobs' credential partition: the same scope opens both."""
    store = open_credential_store(root, KEY, project_id="project-a")
    owner = ModelDefaults(store)
    owner.save(stack(), expected_revision=0)
    same = JobStore(database(root), JobScope(**asdict(store.scope)))
    assert same.trained_default("image") == owner.lane("image")
    other = JobStore(database(root), replace(store.scope, project_id="project-b"))
    assert other.trained_default("image").revision == 0
