# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Schema 10: one atomic upgrade of a real schema 9 store, originals and lane defaults."""

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from threading import Barrier

import pytest

from scenario.core.jobs import store as storage
from scenario.core.jobs.store import (
    JobScope,
    JobStore,
    ResultAsset,
    StoreConflict,
    StoreError,
    TrainedDefaultState,
    TrainedModelDefault,
    TrainedModelPick,
)

# SQL dump of a database written by the schema 9 storage code (tests/fixtures/README.md).
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/synthetic/jobs-schema9.sql"


def materialize(path):
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(FIXTURE.read_text(encoding="utf-8"))
    return path


@pytest.fixture
def schema9(tmp_path):
    return materialize(tmp_path / "jobs.sqlite3")


def _rows(path, table, columns):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(f"SELECT {columns} FROM {table} ORDER BY 1, 2, 3").fetchall()


def _pragma(path, name):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(f"PRAGMA {name}").fetchone()[0]


def _scopes(path):
    scopes = {}
    for key, _, _, raw in _rows(path, "jobs", "scope, request_id, revision, record"):
        scopes[key] = JobScope(**json.loads(raw)["intent"]["scope"])
    return scopes


def _dump(path):
    with closing(sqlite3.connect(path)) as connection:
        return list(connection.iterdump())


def test_fixture_is_the_unmodified_schema_nine_store(schema9):
    assert _pragma(schema9, "user_version") == 9
    assert _pragma(schema9, "application_id") == storage._APPLICATION_ID
    tables = {row[0] for row in _rows(schema9, "sqlite_master", "name, type, sql")}
    assert {"jobs", "film_uploads", "job_film_task"} <= tables
    assert "trained_defaults" not in tables
    assert len(_rows(schema9, "jobs", "scope, request_id, revision")) == 15
    assert len(_scopes(schema9)) == 2
    text = FIXTURE.read_text(encoding="utf-8")
    assert "signed=" not in text and "://" not in text.replace(
        "https://service.example.invalid/v1", ""
    )


def test_real_schema_nine_store_upgrades_every_row_without_guessing(schema9):
    before = _rows(schema9, "jobs", "scope, request_id, revision, record")
    uploads = _rows(schema9, "film_uploads", "scope, production_id, task_id, record")
    scopes = _scopes(schema9)
    stores = {key: JobStore(schema9, scope) for key, scope in scopes.items()}
    assert _pragma(schema9, "user_version") == 10
    after = _rows(schema9, "jobs", "scope, request_id, revision, record")
    assert [row[:3] for row in after] == [row[:3] for row in before]
    for (key, request_id, _, raw), (_, _, _, migrated) in zip(before, after, strict=True):
        expected = json.loads(raw)
        for item in expected["results"]:
            # Earlier stores never declared an original or projection.
            item["asset"].update(source="asset", projection=None)
        assert json.loads(migrated) == expected
        record = stores[key].get(request_id)
        assert json.loads(json.dumps(asdict(record))) == expected
    assert _rows(schema9, "film_uploads", "scope, production_id, task_id, record") == uploads
    assert _rows(schema9, "trained_defaults", "scope, lane, revision, record") == []
    selected = next(store for store in stores.values() if store.scope.project_id)
    reference = selected.film_upload("fixture-production", "upload-one")
    assert reference.asset_id == "fixture-upload-asset"
    assert selected.film_job("fixture-production", "take-one").intent.request_id == "m-film"
    ready = selected.get("j-ready")
    assert [item.asset.media_type for item in ready.results] == [
        "image/png",
        "image/x-exr",
        "image/jpeg",
    ]
    assert {(item.asset.source, item.asset.projection) for item in ready.results} == {
        ("asset", None)
    }
    assert ready.results[0].asset.texture_role == "normal"
    assert ready.intent.mesh_sources[0].mesh_source.objects[0].target_id == "fixture-target"
    applied = selected.get("l-applied")
    assert [item.state.value for item in applied.local_applications] == [
        "applied",
        "failed",
        "applying",
    ]
    with pytest.raises(StoreConflict, match="unfinished"):
        selected.claim_local_application(
            "l-applied",
            expected_revision=applied.revision,
            application_id="after-upgrade",
            destination=applied.intent.origin,
            purpose="images",
            asset_ids=("asset-png",),
        )
    assert selected.get("n-cloud").intent.source == "cloud"
    assert selected.trained_defaults() == ()


def test_upgrade_is_idempotent_and_racing_openers_see_one_migration(schema9):
    scopes = list(_scopes(schema9).values())
    barrier = Barrier(len(scopes))

    def open_store(scope):
        barrier.wait()
        return JobStore(schema9, scope).records()

    with ThreadPoolExecutor(max_workers=len(scopes)) as workers:
        first = list(workers.map(open_store, scopes))
    migrated = _dump(schema9)
    assert _pragma(schema9, "user_version") == 10
    assert [JobStore(schema9, scope).records() for scope in scopes] == first
    assert _dump(schema9) == migrated


@pytest.mark.parametrize(
    "damage",
    ["job-record", "job-revision", "upload-scope", "upload-identity", "upload-task", "commit"],
)
def test_failed_upgrade_of_the_real_store_preserves_every_byte(schema9, monkeypatch, damage):
    scope = next(iter(_scopes(schema9).values()))
    with sqlite3.connect(schema9) as connection:
        if damage == "job-record":
            connection.execute("UPDATE jobs SET record='{}' WHERE request_id='n-cloud'")
        elif damage == "job-revision":
            connection.execute("UPDATE jobs SET revision=99 WHERE request_id='j-ready'")
        elif damage == "upload-scope":
            connection.execute("UPDATE film_uploads SET scope='0'")
        elif damage == "upload-identity":
            connection.execute("UPDATE film_uploads SET task_id='renamed'")
        elif damage == "upload-task":
            # A Film task cannot name both a model job and an upload association.
            connection.execute("UPDATE film_uploads SET task_id='take-one'")
            connection.execute(
                "UPDATE film_uploads SET record=json_set(record, '$.film_task.task_id', 'take-one')"
            )
    before = schema9.read_bytes()
    original = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("synthetic migration commit failure")

    with monkeypatch.context() as patch:
        if damage == "commit":
            patch.setattr(
                sqlite3, "connect", lambda *a, **kw: original(*a, **kw, factory=FailCommit)
            )
        with pytest.raises(StoreError):
            JobStore(schema9, scope)
    assert schema9.read_bytes() == before
    assert _pragma(schema9, "user_version") == 9


def test_schema_ten_is_refused_by_a_schema_nine_reader_and_newer_by_this_one(schema9, monkeypatch):
    scope = next(iter(_scopes(schema9).values()))
    JobStore(schema9, scope)
    upgraded = schema9.read_bytes()
    with monkeypatch.context() as patch:
        # The previous reader's decision: only its own and older versions open.
        patch.setattr(storage, "_VERSION", 9)
        with pytest.raises(StoreError, match="Unsupported"):
            JobStore(schema9, scope)
    assert schema9.read_bytes() == upgraded
    with sqlite3.connect(schema9) as connection:
        connection.execute("PRAGMA user_version=11")
    newer = schema9.read_bytes()
    with pytest.raises(StoreError, match="Unsupported"):
        JobStore(schema9, scope)
    assert schema9.read_bytes() == newer


@pytest.mark.parametrize("missing", ["source", "projection"])
def test_current_schema_requires_source_and_projection_keys(schema9, missing):
    scope = next(scope for scope in _scopes(schema9).values() if scope.project_id)
    store = JobStore(schema9, scope)
    with sqlite3.connect(schema9) as connection:
        raw = connection.execute("SELECT record FROM jobs WHERE request_id='j-ready'").fetchone()
        value = json.loads(raw[0])
        del value["results"][1]["asset"][missing]
        connection.execute(
            "UPDATE jobs SET record=? WHERE request_id='j-ready'", (json.dumps(value),)
        )
    with pytest.raises(StoreError):
        store.get("j-ready")


@pytest.mark.parametrize(
    "changes",
    [
        {"source": "url"},
        {"source": None},
        {"source": "original"},
        {"projection": "cubemap"},
        {"projection": True},
        {"media_type": "model/gltf-binary", "projection": "equirectangular"},
        {"media_type": "image/vnd.radiance", "source": "original"},
        {"media_type": "model/ply", "source": "original"},
    ],
)
def test_result_source_and_projection_are_allowlisted(changes):
    with pytest.raises(ValueError):
        ResultAsset(
            **{"asset_id": "asset", "name": "000-file.bin", "media_type": "image/jpeg"} | changes
        )


@pytest.mark.parametrize("media_type", ["image/x-exr", "image/aces"])
def test_declared_exr_original_keeps_unknown_size_and_projection(media_type):
    asset = ResultAsset(
        "asset", "000-hdr.exr", media_type, source="original", projection="equirectangular"
    )
    assert (asset.expected_size, asset.source, asset.projection) == (
        None,
        "original",
        "equirectangular",
    )


@pytest.fixture
def defaults(tmp_path):
    scope = JobScope("https://service.example.invalid/v1", "local-key-one", "project", "team")
    return JobStore(tmp_path / "jobs.sqlite3", scope)


def stack(lane="image", *picks):
    picks = picks or (TrainedModelPick("model_lora-one", 0.8),)
    return TrainedModelDefault(lane, "stack", "model_base", picks)


def test_trained_default_revisions_survive_clear_and_reopen(defaults, tmp_path):
    assert defaults.trained_default("image") == TrainedDefaultState("image", 0)
    saved = defaults.set_trained_default(stack(), expected_revision=0)
    assert saved == TrainedDefaultState("image", 1, stack())
    reopened = JobStore(tmp_path / "jobs.sqlite3", defaults.scope)
    assert reopened.trained_default("image") == saved
    composition = TrainedModelDefault(
        "image", "composition", "model_base", (TrainedModelPick("model_composition"),)
    )
    changed = reopened.set_trained_default(composition, expected_revision=1)
    with pytest.raises(StoreConflict):
        defaults.set_trained_default(stack(), expected_revision=1)
    cleared = defaults.clear_trained_default("image", expected_revision=changed.revision)
    assert cleared == TrainedDefaultState("image", 3)
    # A writer holding a pre-clear revision cannot resurrect its stale choice.
    for revision in (0, 1, 2):
        with pytest.raises(StoreConflict):
            defaults.set_trained_default(stack(), expected_revision=revision)
    assert defaults.clear_trained_default("image", expected_revision=3) == cleared
    assert defaults.set_trained_default(stack(), expected_revision=3).revision == 4
    assert defaults.trained_defaults() == (TrainedDefaultState("image", 4, stack()),)


def test_trained_defaults_list_only_saved_lanes_in_lane_order(defaults):
    custom = TrainedModelDefault("render_image", "custom", "model_private")
    defaults.set_trained_default(custom, expected_revision=0)
    defaults.set_trained_default(stack(), expected_revision=0)
    defaults.set_trained_default(stack("video"), expected_revision=0)
    defaults.clear_trained_default("video", expected_revision=1)
    assert [state.lane for state in defaults.trained_defaults()] == ["image", "render_image"]


@pytest.mark.parametrize(
    "change",
    [
        {"account_id": "local-key-two"},
        {"project_id": None},
        {"project_id": "other-project"},
        {"team_id": None},
        {"service": "https://other.example.invalid/v1"},
    ],
)
def test_trained_defaults_are_isolated_by_credential_scope_and_project(defaults, tmp_path, change):
    saved = defaults.set_trained_default(stack(), expected_revision=0)
    other = JobStore(tmp_path / "jobs.sqlite3", replace(defaults.scope, **change))
    assert other.trained_default("image") == TrainedDefaultState("image", 0)
    assert other.trained_defaults() == ()
    with pytest.raises(StoreConflict):
        other.clear_trained_default("image", expected_revision=1)
    other.set_trained_default(stack("image", TrainedModelPick("model_other")), expected_revision=0)
    assert defaults.trained_default("image") == saved


def test_racing_default_writers_cannot_both_win(defaults):
    barrier = Barrier(2)

    def save(model_id):
        barrier.wait()
        try:
            return defaults.set_trained_default(
                stack("image", TrainedModelPick(model_id)), expected_revision=0
            )
        except StoreConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(save, ["model_first", "model_second"]))
    winners = [outcome for outcome in outcomes if outcome is not None]
    assert len(winners) == 1
    assert defaults.trained_default("image") == winners[0]


def test_failed_default_commit_preserves_the_previous_choice(defaults, tmp_path, monkeypatch):
    saved = defaults.set_trained_default(stack(), expected_revision=0)
    before = (tmp_path / "jobs.sqlite3").read_bytes()
    original = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("synthetic commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", lambda *a, **kw: original(*a, **kw, factory=FailCommit))
        with pytest.raises(StoreError):
            defaults.clear_trained_default("image", expected_revision=1)
    assert (tmp_path / "jobs.sqlite3").read_bytes() == before
    assert defaults.trained_default("image") == saved


@pytest.mark.parametrize(
    "damage",
    ["json", "scope", "lane", "revision", "extra", "picks", "scale", "route", "missing-pick-key"],
)
def test_corrupt_trained_default_is_preserved_and_rejected(defaults, tmp_path, damage):
    defaults.set_trained_default(stack(), expected_revision=0)
    path = tmp_path / "jobs.sqlite3"
    with sqlite3.connect(path) as connection:
        value = json.loads(connection.execute("SELECT record FROM trained_defaults").fetchone()[0])
        revision = 1
        if damage == "scope":
            value["scope"]["project_id"] = "other-project"
        elif damage == "lane":
            value["default"]["lane"] = "video"
        elif damage == "revision":
            revision = 0
        elif damage == "extra":
            value["default"]["prompt"] = "private prompt"
        elif damage == "picks":
            value["default"]["picks"] = [value["default"]["picks"][0]] * 2
        elif damage == "scale":
            value["default"]["picks"][0]["scale"] = "0.8"
        elif damage == "route":
            value["default"]["route"] = "composition"
        elif damage == "missing-pick-key":
            del value["default"]["picks"][0]["scale"]
        raw = "{" if damage == "json" else json.dumps(value)
        connection.execute("UPDATE trained_defaults SET record=?, revision=?", (raw, revision))
    corrupted = path.read_bytes()
    with pytest.raises(StoreError, match="trained-model default"):
        defaults.trained_default("image")
    with pytest.raises(StoreError):
        defaults.trained_defaults()
    with pytest.raises(StoreError):
        defaults.set_trained_default(stack(), expected_revision=1)
    assert path.read_bytes() == corrupted


def test_cleared_default_with_a_corrupt_lane_key_is_not_hidden(defaults, tmp_path):
    saved = defaults.set_trained_default(stack(), expected_revision=0)
    defaults.clear_trained_default("image", expected_revision=saved.revision)
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        connection.execute("UPDATE trained_defaults SET lane='../image'")
    with pytest.raises(StoreError, match="trained-model default"):
        defaults.trained_defaults()


@pytest.mark.parametrize(
    "build",
    [
        lambda: TrainedModelDefault("Image", "stack", "model_base", (TrainedModelPick("m"),)),
        lambda: TrainedModelDefault("image/lane", "custom", "model_base"),
        lambda: TrainedModelDefault("image", "train", "model_base"),
        lambda: TrainedModelDefault("image", "stack", "model_base"),
        lambda: TrainedModelDefault("image", "stack", "model_base", [TrainedModelPick("m")]),
        lambda: TrainedModelDefault("image", "custom", "model_base", (TrainedModelPick("m"),)),
        lambda: TrainedModelDefault("image", "direct", "model_base", (TrainedModelPick("m"),)),
        lambda: TrainedModelDefault(
            "image", "composition", "model_base", (TrainedModelPick("m", 1.0),)
        ),
        lambda: TrainedModelDefault(
            "image", "composition", "model_base", (TrainedModelPick("a"), TrainedModelPick("b"))
        ),
        lambda: TrainedModelDefault(
            "image", "stack", "model_base", (TrainedModelPick("m"), TrainedModelPick("m"))
        ),
        lambda: TrainedModelDefault(
            "image", "stack", "model_base", (TrainedModelPick("model_base"),)
        ),
        lambda: TrainedModelDefault(
            "image",
            "stack",
            "model_base",
            tuple(TrainedModelPick(f"model_{index}") for index in range(17)),
        ),
        lambda: TrainedModelDefault("image", "custom", "https://private.invalid/model"),
        lambda: TrainedModelPick("model", 1),
        lambda: TrainedModelPick("model", True),
        lambda: TrainedModelPick("model", float("nan")),
        lambda: TrainedModelPick("model", float("inf")),
        lambda: TrainedModelPick("model?token=secret"),
    ],
)
def test_invalid_trained_defaults_are_rejected_before_storage(build):
    with pytest.raises(ValueError):
        build()


def test_trained_default_storage_holds_identities_without_raw_metadata(defaults, tmp_path):
    defaults.set_trained_default(stack(), expected_revision=0)
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        key, lane, revision, raw = connection.execute(
            "SELECT scope, lane, revision, record FROM trained_defaults"
        ).fetchone()
    assert key == hashlib.sha256(storage._json(asdict(defaults.scope)).encode()).hexdigest()
    assert (lane, revision) == ("image", 1)
    assert json.loads(raw) == {
        "scope": asdict(defaults.scope),
        "default": {
            "lane": "image",
            "route": "stack",
            "base_model_id": "model_base",
            "picks": [{"model_id": "model_lora-one", "scale": 0.8}],
        },
    }
    with pytest.raises(ValueError):
        defaults.set_trained_default({"lane": "image"}, expected_revision=0)
    with pytest.raises(ValueError):
        defaults.clear_trained_default("image", expected_revision=-1)
    with pytest.raises(ValueError):
        defaults.trained_default("../image")
