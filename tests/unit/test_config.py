# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import datetime as dt

from scenario.core import config


def test_preferences_ignore_ambient_environment():
    creds = config.resolve_credentials(
        " pref_key ",
        "pref_secret",
        environ={"SCENARIO_API_KEY": "env_key", "SCENARIO_API_SECRET": "env_secret"},
    )
    assert (creds.key, creds.secret) == ("pref_key", "pref_secret")
    assert creds.valid


def test_environment_requires_explicit_selection():
    creds = config.resolve_credentials(
        "pref_key",
        "pref_secret",
        source="ENVIRONMENT",
        environ={"SCENARIO_API_KEY": " env_key ", "SCENARIO_API_SECRET": "env_secret"},
    )
    assert (creds.key, creds.secret) == ("env_key", "env_secret")
    assert creds.valid


def test_partial_environment_never_borrows_from_saved_preferences():
    for env in (
        {},
        {"SCENARIO_API_KEY": "k"},
        {"SCENARIO_API_SECRET": "s"},
        {"SCENARIO_API_KEY": "k", "SCENARIO_API_SECRET": " "},
    ):
        creds = config.resolve_credentials("pref_key", "pref_secret", env, source="ENVIRONMENT")
        assert not creds.valid
        assert "pref_key" not in (creds.key, creds.secret)
        assert "pref_secret" not in (creds.key, creds.secret)


def test_partial_preferences_never_borrow_from_environment():
    env = {"SCENARIO_API_KEY": "env_key", "SCENARIO_API_SECRET": "env_secret"}
    for key, secret in ((None, None), ("k", ""), ("", "s")):
        assert not config.resolve_credentials(key, secret, env).valid


def test_unknown_source_is_rejected_and_credentials_are_not_in_repr():
    import pytest

    with pytest.raises(ValueError, match="Unknown credential source"):
        config.resolve_credentials("k", "s", source="invalid")
    representation = repr(config.Credentials("sensitive-key", "sensitive-secret"))
    assert "sensitive" not in representation


def test_paths_layout(tmp_path):
    paths = config.Paths(
        state_dir=tmp_path / "state", cache_dir=tmp_path / "cache", output_dir=tmp_path / "out"
    )
    assert paths.models_cache_dir == tmp_path / "cache" / "models"
    assert paths.registry_file == tmp_path / "state" / "jobs.json"
    when = dt.datetime(2026, 8, 28, 9, 30, 5)
    assert paths.output_for("image", when) == tmp_path / "out" / "images" / "20260828"
    assert paths.output_for("3d", when) == tmp_path / "out" / "3d" / "20260828"
    assert paths.output_for("material", when) == tmp_path / "out" / "materials" / "20260828"
    assert paths.output_for("weird", when) == tmp_path / "out" / "other" / "20260828"
    today = f"{dt.datetime.now():%Y%m%d}"
    assert paths.output_for("video").name == today


def test_ext_for_mime():
    assert config.ext_for_mime("image/png") == "png"
    assert config.ext_for_mime("model/gltf-binary") == "glb"
    assert config.ext_for_mime("video/mp4") == "mp4"
    assert config.ext_for_mime("application/x-unknown") == "bin"
    assert config.ext_for_mime(None) == "bin"


def test_output_filename_is_readable_and_unique():
    when = dt.datetime(2026, 8, 28, 9, 30, 5)
    name = config.output_filename(
        "image", "model_patina-material", "job_KWxxsnSdVXDFZRMsoCvLTmKY", 2, "png", when=when
    )
    assert name == "20260828_093005_patina-material_soCvLTmKY_02.png"
    with_asset = config.output_filename(
        "3d", "model_hitem-3d-split", "job_x", 0, "glb", when=when, asset_id="asset_ccpDR7Ga1Q2w"
    )
    assert with_asset == "20260828_093005_hitem-3d-split_asset_ccpDR7Ga1Q2w_00.glb"
    assert config.slug("model_Google Gemini 3.1 🍌", limit=12) == "google-gemin"
