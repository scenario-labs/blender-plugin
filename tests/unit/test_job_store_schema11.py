# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Schema 11: WAV originals, and the 10 -> 11 upgrade older readers refuse."""

import json
import sqlite3
from contextlib import closing

import pytest

from scenario.core.jobs import store as storage
from scenario.core.jobs.store import (
    JobStore,
    ResultAsset,
    StoreError,
    TrainedModelDefault,
    TrainedModelPick,
)
from tests.unit.test_job_store_schema10 import _dump, _pragma, _rows, _scopes, materialize


@pytest.mark.parametrize("media_type", ["audio/wav", "audio/x-wav"])
def test_declared_wav_original_keeps_unknown_size_and_no_projection(media_type):
    asset = ResultAsset("asset", "000-sound.wav", media_type, source="original")
    assert (asset.expected_size, asset.source, asset.projection, asset.texture_role) == (
        None,
        "original",
        None,
        None,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"media_type": "audio/mpeg", "source": "original"},
        {"media_type": "audio/flac", "source": "original"},
        {"media_type": "audio/ogg", "source": "original"},
        {"media_type": "audio/wav", "source": "original", "projection": "equirectangular"},
        {"media_type": "audio/wav", "source": "original", "texture_role": "base"},
    ],
)
def test_only_wav_audio_originals_are_stored(changes):
    with pytest.raises(ValueError):
        ResultAsset(**{"asset_id": "asset", "name": "000-sound.wav"} | changes)


@pytest.fixture
def schema10(tmp_path):
    """A schema 10 store: rows in the shape schema 10 code wrote, with a lane default.

    Schema 11 changes no field, only which values a result may hold, so the
    upgraded schema 9 fixture without schema 12's claim time, plus a saved
    default, is exactly a schema 10 file.
    """
    path = materialize(tmp_path / "jobs.sqlite3")
    scope = next(scope for scope in _scopes(path).values() if scope.project_id)
    JobStore(path, scope).set_trained_default(
        TrainedModelDefault(
            "image", "stack", "model_base", (TrainedModelPick("model_lora", 0.75),)
        ),
        expected_revision=0,
    )
    with closing(sqlite3.connect(path)) as connection:
        # Schema 12 added the claim time and result parents; a schema 10 row has neither.
        for request_id, scope_key, raw in connection.execute(
            "SELECT request_id, scope, record FROM jobs"
        ).fetchall():
            value = json.loads(raw)
            del value["claimed_at"]
            for item in value["results"]:
                del item["asset"]["parent_id"]
            connection.execute(
                "UPDATE jobs SET record=? WHERE request_id=? AND scope=?",
                (json.dumps(value), request_id, scope_key),
            )
        connection.execute("PRAGMA user_version=10")
        connection.commit()
    return path


def test_schema_ten_store_upgrades_without_changing_any_row(schema10):
    jobs = _rows(schema10, "jobs", "scope, request_id, revision, record")
    uploads = _rows(schema10, "film_uploads", "scope, production_id, task_id, record")
    defaults = _rows(schema10, "trained_defaults", "scope, lane, revision, record")
    assert defaults
    stores = {key: JobStore(schema10, scope) for key, scope in _scopes(schema10).items()}
    assert _pragma(schema10, "user_version") == storage._VERSION
    # Only schema 12's unknown claim time and result parents are added to each row.
    upgraded = _rows(schema10, "jobs", "scope, request_id, revision, record")
    assert [row[:3] for row in upgraded] == [row[:3] for row in jobs]
    for (*_, raw), (*_, migrated) in zip(jobs, upgraded, strict=True):
        expected = json.loads(raw) | {"claimed_at": None}
        for item in expected["results"]:
            item["asset"]["parent_id"] = None
        assert json.loads(migrated) == expected
    assert _rows(schema10, "film_uploads", "scope, production_id, task_id, record") == uploads
    assert _rows(schema10, "trained_defaults", "scope, lane, revision, record") == defaults
    selected = next(store for store in stores.values() if store.scope.project_id)
    assert selected.trained_default("image").default.picks[0].scale == 0.75
    migrated = _dump(schema10)
    JobStore(schema10, selected.scope)
    assert _dump(schema10) == migrated


@pytest.mark.parametrize("damage", ["job-record", "default-record", "default-scope"])
def test_failed_schema_ten_upgrade_preserves_every_byte(schema10, damage):
    scope = next(iter(_scopes(schema10).values()))
    with sqlite3.connect(schema10) as connection:
        if damage == "job-record":
            connection.execute("UPDATE jobs SET record='{}' WHERE request_id='n-cloud'")
        elif damage == "default-record":
            connection.execute("UPDATE trained_defaults SET record='{}'")
        else:
            connection.execute("UPDATE trained_defaults SET scope='0'")
    before = schema10.read_bytes()
    with pytest.raises(StoreError):
        JobStore(schema10, scope)
    assert schema10.read_bytes() == before
    assert _pragma(schema10, "user_version") == 10


def test_schema_eleven_is_refused_by_a_schema_ten_reader_and_newer_by_this_one(
    schema10, monkeypatch
):
    scope = next(iter(_scopes(schema10).values()))
    JobStore(schema10, scope)
    upgraded = schema10.read_bytes()
    with monkeypatch.context() as patch:
        # 0.10.x: a schema 10 reader refuses the store as a newer format, not as damage.
        patch.setattr(storage, "_VERSION", 10)
        with pytest.raises(StoreError, match="Unsupported"):
            JobStore(schema10, scope)
    assert schema10.read_bytes() == upgraded
    with sqlite3.connect(schema10) as connection:
        connection.execute(f"PRAGMA user_version={storage._VERSION + 1}")
    newer = schema10.read_bytes()
    with pytest.raises(StoreError, match="Unsupported"):
        JobStore(schema10, scope)
    assert schema10.read_bytes() == newer
