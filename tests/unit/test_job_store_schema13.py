# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Schema 13: the generation lane saved with each job and the 12 -> 13 upgrade."""

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

import pytest

from scenario.core.api.catalog import GENERATION_LANES
from scenario.core.jobs import store as storage
from scenario.core.jobs.store import JobIntent, JobOrigin, JobScope, JobStore, StoreError
from tests.unit.test_job_store_schema10 import _dump, _pragma, _rows, _scopes

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
    """A schema 12 row as the upgrade rewrites it: a local intent with an unknown lane."""
    expected = json.loads(raw)
    if expected["intent"].get("source") != "cloud":
        expected["intent"]["lane"] = None
    return expected


def test_fixture_is_the_unmodified_schema_twelve_store(schema12):
    assert _pragma(schema12, "user_version") == 12
    assert _pragma(schema12, "application_id") == storage._APPLICATION_ID
    assert len(_rows(schema12, "jobs", "scope, request_id, revision")) == 19
    assert len(_rows(schema12, "trained_defaults", "scope, lane, revision")) == 1
    assert len(_scopes(schema12)) == 2
    values = [json.loads(raw) for *_, raw in _rows(schema12, "jobs", "scope, request_id, record")]
    assert all("lane" not in value["intent"] for value in values)
    assert any(value["claimed_at"] for value in values)
    assert any(item["asset"]["parent_id"] for value in values for item in value["results"])


def test_real_schema_twelve_store_upgrades_every_row_with_an_unknown_lane(schema12):
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
