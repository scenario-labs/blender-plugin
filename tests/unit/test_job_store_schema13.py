# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Schema 13: the generation lane saved with each job, on-demand copies of another result
fetched after the job is complete, and the 12 -> 13 upgrade."""

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from scenario.core.api.catalog import GENERATION_LANES
from scenario.core.jobs import store as storage
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    LocalApplicationState,
    ResultAsset,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.transfers import DownloadedResult
from tests.unit.test_job_store_schema10 import _dump, _pragma, _rows, _scopes
from tests.unit.test_job_store_schema12 import _succeeded

# SQL dump of a database written by the schema 12 release's storage code.
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/synthetic/jobs-schema12.sql"


def materialize(path):
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(FIXTURE.read_text(encoding="utf-8"))
    return path


@pytest.fixture
def schema12(tmp_path):
    return materialize(tmp_path / "jobs.sqlite3")


@pytest.fixture
def scope():
    return JobScope("https://service.example.invalid/v1", "local-key-one", "project-one")


@pytest.fixture
def store(tmp_path, scope):
    return JobStore(tmp_path / "jobs.sqlite3", scope)


def _intent(scope, request_id="request", lane=None):
    return JobIntent(
        request_id,
        scope,
        JobOrigin("file", "scene", "revision", "target"),
        "model",
        "model_target",
        "a" * 64,
        "b" * 64,
        "1.5",
        lane=lane,
    )


def _upgraded(raw):
    """A schema 12 row as the upgrade rewrites it: a local intent with an unknown lane,
    and no result waiting for a fetch."""
    expected = json.loads(raw)
    if expected["intent"].get("source") != "cloud":
        expected["intent"]["lane"] = None
    for item in expected["results"]:
        item["asset"]["on_demand"] = False
    return expected


def test_fixture_is_the_unmodified_schema_twelve_store(schema12):
    assert _pragma(schema12, "user_version") == 12
    assert _pragma(schema12, "application_id") == storage._APPLICATION_ID
    assert len(_rows(schema12, "jobs", "scope, request_id, revision")) == 19
    assert len(_rows(schema12, "trained_defaults", "scope, lane, revision")) == 1
    assert len(_scopes(schema12)) == 2
    values = [json.loads(raw) for *_, raw in _rows(schema12, "jobs", "scope, request_id, record")]
    assert all("lane" not in value["intent"] for value in values)
    assert all("on_demand" not in item["asset"] for value in values for item in value["results"])
    assert any(value["claimed_at"] for value in values)
    assert any(item["asset"]["parent_id"] for value in values for item in value["results"])


def test_real_schema_twelve_store_upgrades_every_row_with_an_unknown_lane_and_no_fetch(
    schema12,
):
    before = _rows(schema12, "jobs", "scope, request_id, revision, record")
    uploads = _rows(schema12, "film_uploads", "scope, production_id, task_id, record")
    defaults = _rows(schema12, "trained_defaults", "scope, lane, revision, record")
    stores = {key: JobStore(schema12, scope) for key, scope in _scopes(schema12).items()}
    assert _pragma(schema12, "user_version") == storage._VERSION == 13
    after = _rows(schema12, "jobs", "scope, request_id, revision, record")
    assert [row[:3] for row in after] == [row[:3] for row in before]
    for (key, request_id, _, raw), (*_, migrated) in zip(before, after, strict=True):
        expected = _upgraded(raw)
        assert json.loads(migrated) == expected
        record = stores[key].get(request_id)
        assert record.intent.lane is None
        assert not any(item.asset.on_demand for item in record.results)
        assert json.loads(json.dumps(asdict(record))) == expected
    assert _rows(schema12, "film_uploads", "scope, production_id, task_id, record") == uploads
    assert _rows(schema12, "trained_defaults", "scope, lane, revision, record") == defaults
    selected = next(store for store in stores.values() if store.scope.project_id)
    assert selected.get("q-claimed").claimed_at == "2026-10-14T21:18:11.123Z"
    parents = {
        item.asset.asset_id: item.asset.parent_id for item in selected.get("r-parents").results
    }
    assert parents == {"asset-glb": None, "asset-obj": "asset-glb"}
    assert selected.get("n-cloud").intent.source == "cloud"
    migrated = _dump(schema12)
    JobStore(schema12, selected.scope)
    assert _dump(schema12) == migrated


@pytest.mark.parametrize("damage", ["job-record", "default-record"])
def test_failed_schema_twelve_upgrade_preserves_every_byte(schema12, damage):
    scope = next(iter(_scopes(schema12).values()))
    with sqlite3.connect(schema12) as connection:
        if damage == "job-record":
            connection.execute("UPDATE jobs SET record='{}' WHERE request_id='q-claimed'")
        else:
            connection.execute("UPDATE trained_defaults SET record='{}'")
    before = schema12.read_bytes()
    with pytest.raises(StoreError):
        JobStore(schema12, scope)
    assert schema12.read_bytes() == before
    assert _pragma(schema12, "user_version") == 12


@pytest.mark.parametrize("request_id", ["q-claimed", "n-cloud"])
def test_schema_twelve_row_that_already_names_a_lane_is_refused(schema12, request_id):
    scope = next(iter(_scopes(schema12).values()))
    with sqlite3.connect(schema12) as connection:
        (raw,) = connection.execute(
            "SELECT record FROM jobs WHERE request_id=?", (request_id,)
        ).fetchone()
        value = json.loads(raw)
        value["intent"]["lane"] = "image"
        connection.execute(
            "UPDATE jobs SET record=? WHERE request_id=?", (json.dumps(value), request_id)
        )
    before = schema12.read_bytes()
    with pytest.raises(StoreError):
        JobStore(schema12, scope)
    assert schema12.read_bytes() == before


def test_schema_twelve_result_that_already_waits_for_a_fetch_is_refused(schema12):
    scope = next(iter(_scopes(schema12).values()))
    with sqlite3.connect(schema12) as connection:
        (raw,) = connection.execute(
            "SELECT record FROM jobs WHERE request_id='r-parents'"
        ).fetchone()
        value = json.loads(raw)
        value["results"][1]["asset"]["on_demand"] = True
        connection.execute(
            "UPDATE jobs SET record=? WHERE request_id='r-parents'", (json.dumps(value),)
        )
    before = schema12.read_bytes()
    with pytest.raises(StoreError):
        JobStore(schema12, scope)
    assert schema12.read_bytes() == before


def test_schema_thirteen_is_refused_by_a_schema_twelve_reader_and_newer_by_this_one(
    schema12, monkeypatch
):
    scope = next(iter(_scopes(schema12).values()))
    JobStore(schema12, scope)
    upgraded = schema12.read_bytes()
    with monkeypatch.context() as patch:
        # The schema 12 release refuses the store as a newer format, not as damage.
        patch.setattr(storage, "_VERSION", 12)
        with pytest.raises(StoreError, match="Unsupported"):
            JobStore(schema12, scope)
    assert schema12.read_bytes() == upgraded
    with sqlite3.connect(schema12) as connection:
        connection.execute(f"PRAGMA user_version={storage._VERSION + 1}")
    newer = schema12.read_bytes()
    with pytest.raises(StoreError, match="Unsupported"):
        JobStore(schema12, scope)
    assert schema12.read_bytes() == newer


def test_fresh_store_starts_at_schema_thirteen(tmp_path, scope):
    JobStore(tmp_path / "jobs.sqlite3", scope)
    assert _pragma(tmp_path / "jobs.sqlite3", "user_version") == 13


@pytest.mark.parametrize("lane", [*GENERATION_LANES, "workflow", "film"])
def test_the_submitting_lane_is_saved_and_reopens(store, tmp_path, lane):
    record = store.create(_intent(store.scope, lane=lane))
    assert record.intent.lane == lane
    reopened = JobStore(tmp_path / "jobs.sqlite3", store.scope).get("request")
    assert reopened == record
    with closing(sqlite3.connect(tmp_path / "jobs.sqlite3")) as connection:
        (raw,) = connection.execute("SELECT record FROM jobs").fetchone()
    assert json.loads(raw)["intent"]["lane"] == lane


@pytest.mark.parametrize("lane", ["", "Image", "bad/lane", "has space", 3])
def test_lane_is_a_bounded_lowercase_identifier(scope, lane):
    with pytest.raises(ValueError):
        _intent(scope, lane=lane)


def test_cloud_intents_name_no_lane(store):
    origin = JobOrigin("file", "scene", "revision")
    cloud = storage.CloudJobIntent("cloud", store.scope, origin, "model_fixture")
    assert cloud.lane is None
    assert "lane" not in asdict(cloud)


def test_schema_thirteen_row_without_a_lane_is_invalid_data(store, tmp_path):
    store.create(_intent(store.scope, lane="image"))
    with closing(sqlite3.connect(tmp_path / "jobs.sqlite3")) as connection, connection:
        (raw,) = connection.execute("SELECT record FROM jobs").fetchone()
        value = json.loads(raw)
        del value["intent"]["lane"]
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    with pytest.raises(StoreError):
        store.get("request")


DESTINATION = JobOrigin("file", "scene", "revision", "target")


def _receipt(asset, size=1):
    return DownloadedResult(asset.name, size, hashlib.sha256(asset.asset_id.encode()).hexdigest())


def _package():
    """A GLB, then the OBJ and MTL Scenario derives from it, which wait for a fetch."""
    return (
        ResultAsset("glb", "000-glb.glb", "model/gltf-binary", 1),
        ResultAsset("obj", "001-obj.obj", "model/obj", 1, parent_id="glb", on_demand=True),
        ResultAsset("mtl", "002-mtl.mtl", "model/mtl", 1, parent_id="glb", on_demand=True),
    )


def _ready(store):
    record = _succeeded(store)
    record = store.set_results("request", _package(), expected_revision=record.revision)
    record = store.transition(
        "request", expected_revision=record.revision, state=JobState.DOWNLOADING
    )
    glb = record.results[0].asset
    record = store.record_download(
        "request", "glb", _receipt(glb), expected_revision=record.revision
    )
    return store.transition("request", expected_revision=record.revision, state=JobState.READY)


def _applied(store):
    record = _ready(store)
    for state in (JobState.APPLYING, JobState.APPLIED):
        record = store.transition("request", expected_revision=record.revision, state=state)
    return record


def _fetch(store, record, asset_id):
    asset = next(item.asset for item in record.results if item.asset.asset_id == asset_id)
    return store.record_fetch(
        "request", asset_id, _receipt(asset), expected_revision=record.revision
    )


def _reuse(store, record, application_id):
    record = store.claim_local_application(
        "request",
        expected_revision=record.revision,
        application_id=application_id,
        destination=DESTINATION,
        purpose="model",
        asset_ids=("glb",),
    )
    return store.finish_local_application(
        "request",
        expected_revision=record.revision,
        application_id=application_id,
        state=LocalApplicationState.APPLIED,
    )


@pytest.mark.parametrize("change", [{"parent_id": None}, {"on_demand": 1}])
def test_only_a_copy_of_another_result_waits_for_a_fetch(change):
    with pytest.raises(ValueError):
        replace(_package()[1], **change)


def test_a_job_is_ready_while_its_on_demand_copies_wait(store):
    record = _ready(store)
    assert record.state == JobState.READY
    assert [item.receipt is None for item in record.results] == [False, True, True]
    assert JobStore(store._path, store.scope).get("request") == record


def test_the_job_download_never_records_an_on_demand_copy(store):
    record = _succeeded(store)
    record = store.set_results("request", _package(), expected_revision=record.revision)
    record = store.transition(
        "request", expected_revision=record.revision, state=JobState.DOWNLOADING
    )
    with pytest.raises(ValueError, match="waits for a fetch"):
        store.record_download(
            "request", "obj", _receipt(record.results[1].asset), expected_revision=record.revision
        )
    with pytest.raises(ValueError, match="receipt"):
        store.transition("request", expected_revision=record.revision, state=JobState.READY)


def test_a_fetch_saves_the_copy_and_keeps_the_job_state(store):
    record = _ready(store)
    fetched = _fetch(store, record, "obj")
    assert (fetched.state, fetched.revision) == (JobState.READY, record.revision + 1)
    assert fetched.results[1].receipt == _receipt(record.results[1].asset)
    assert fetched.results[2].receipt is None
    assert store.get("request") == fetched
    with pytest.raises(ValueError, match="already has a receipt"):
        _fetch(store, fetched, "obj")
    with pytest.raises(ValueError, match="not on demand"):
        store.record_fetch(
            "request", "glb", _receipt(record.results[0].asset), expected_revision=fetched.revision
        )


def test_a_fetched_obj_takes_its_saved_size(store):
    record = _ready(store)
    asset = record.results[1].asset
    fetched = store.record_fetch(
        "request",
        "obj",
        _receipt(asset, size=7),
        expected_revision=record.revision,
        allow_mesh_size_correction=True,
    )
    assert fetched.results[1].asset.expected_size == 7


def test_no_fetch_while_the_job_downloads_or_applies(store):
    record = _ready(store)
    applying = store.transition(
        "request", expected_revision=record.revision, state=JobState.APPLYING
    )
    with pytest.raises(StoreConflict):
        _fetch(store, applying, "obj")
    failed = store.transition(
        "request", expected_revision=applying.revision, state=JobState.APPLY_FAILED
    )
    assert _fetch(store, failed, "obj").state == JobState.APPLY_FAILED


def test_no_fetch_while_a_reuse_is_unfinished(store):
    record = _applied(store)
    claimed = store.claim_local_application(
        "request",
        expected_revision=record.revision,
        application_id="reuse",
        destination=DESTINATION,
        purpose="model",
        asset_ids=("glb",),
    )
    with pytest.raises(StoreConflict):
        _fetch(store, claimed, "obj")
    # The claim's own revision still finishes it.
    finished = store.finish_local_application(
        "request",
        expected_revision=claimed.revision,
        application_id="reuse",
        state=LocalApplicationState.APPLIED,
    )
    assert finished.local_applications[-1].state == LocalApplicationState.APPLIED


def test_fetches_between_reuses_keep_the_reuse_history_valid(store):
    record = _reuse(store, _applied(store), "first")
    record = _fetch(store, record, "obj")
    record = _fetch(store, record, "mtl")
    record = _reuse(store, record, "second")
    assert [item.source_revision for item in record.local_applications] == [9, 13]
    assert JobStore(store._path, store.scope).get("request") == record


def test_a_reuse_history_gap_no_fetch_explains_is_invalid_data(store):
    record = _reuse(store, _applied(store), "first")
    with sqlite3.connect(store._path) as connection:
        value = asdict(replace(record, revision=record.revision + 1))
        connection.execute(
            "UPDATE jobs SET revision=?, record=?", (value["revision"], json.dumps(value))
        )
    with pytest.raises(StoreError):
        store.get("request")
