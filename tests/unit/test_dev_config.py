# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline credential boundaries, including executable entry points and uv loading."""

import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from tools.dev_config import live_settings

ROOT = Path(__file__).resolve().parents[2]


def test_test_credentials_do_not_fall_back_to_runtime_credentials():
    with pytest.raises(SystemExit, match="no test credentials"):
        live_settings({"SCENARIO_API_KEY": "runtime", "SCENARIO_API_SECRET": "runtime"})


@pytest.mark.parametrize("project", [None, "", "  "])
def test_api_keys_work_without_project(project):
    env = {"SCENARIO_TEST_API_KEY": " test-key ", "SCENARIO_TEST_API_SECRET": "test-secret"}
    if project is not None:
        env["SCENARIO_TEST_PROJECT_ID"] = project
    settings = live_settings(env)
    assert settings.project_id is None
    assert settings.credentials.key == "test-key"
    assert "test-key" not in repr(settings)
    assert "test-secret" not in repr(settings)


def test_project_selection_is_preserved_and_not_silently_ignored():
    env = {
        "SCENARIO_TEST_API_KEY": "key",
        "SCENARIO_TEST_API_SECRET": "secret",
        "SCENARIO_TEST_PROJECT_ID": " selected-project ",
    }
    assert live_settings(env).project_id == "selected-project"
    assert live_settings(env).credentials.valid


@pytest.mark.parametrize("key,secret", [("", ""), ("key", ""), ("", "secret"), ("  ", "secret")])
def test_missing_credentials_fail_without_disclosing_values(key, secret):
    with pytest.raises(SystemExit) as exc:
        live_settings({"SCENARIO_TEST_API_KEY": key, "SCENARIO_TEST_API_SECRET": secret})
    assert str(exc.value).startswith("no test credentials:")
    assert "\n" not in str(exc.value)


@pytest.mark.parametrize(
    "script",
    [
        "tools/audit_payloads.py",
        "tools/record_fixtures.py",
        *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "tests/smoke").glob("*.py"))],
    ],
)
def test_entry_points_reject_missing_credentials_before_client_creation(script, monkeypatch):
    from scenario.core.api import client, sdk_adapter

    def forbidden(*args, **kwargs):
        pytest.fail("must validate credentials before constructing a client")

    monkeypatch.setattr(client, "ScenarioClient", forbidden)
    monkeypatch.setattr(sdk_adapter, "SDKAdapter", forbidden)
    for name in os.environ:
        if name.startswith("SCENARIO_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("SCENARIO_SMOKE", "1")
    monkeypatch.setattr("sys.argv", [script])
    with pytest.raises(SystemExit, match="no test credentials"):
        runpy.run_path(str(ROOT / script), run_name="__main__")


def test_uv_dotenv_precedence_and_no_file_loading(tmp_path):
    dotenv = tmp_path / ".env.local"
    dotenv.write_text("SCENARIO_TEST_API_KEY=file-key\nSCENARIO_TEST_API_SECRET='file-secret'\n")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SCENARIO_", "UV_ENV", "UV_NO_ENV"))
    }
    env["SCENARIO_TEST_API_KEY"] = "process-key"
    # Keep alternate-interpreter runs from replacing the active test environment
    # with the default .python-version interpreter while pytest is still using it.
    command = ["uv", "run", "--locked", "--offline", "--python", sys.executable]
    code = (
        "from tools.dev_config import live_settings; s=live_settings(); "
        "assert s.credentials.key == 'process-key'; "
        "assert s.credentials.secret == 'file-secret'; assert s.project_id is None"
    )
    result = subprocess.run(
        command + ["--env-file", str(dotenv), "python", "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    # Even a user-configured UV_ENV_FILE cannot make an offline command read secrets.
    env["UV_ENV_FILE"] = str(dotenv)
    result = subprocess.run(
        command
        + [
            "--no-env-file",
            "python",
            "-c",
            "from tools.dev_config import live_settings; live_settings()",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stderr.startswith("no test credentials:")


@pytest.mark.parametrize("project", [None, "", " selected-project "])
@pytest.mark.parametrize(
    "script",
    [
        "tools/audit_payloads.py",
        "tools/record_fixtures.py",
        *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "tests/smoke").glob("*.py"))],
    ],
)
def test_live_tools_pass_selected_pair_explicitly(script, project, monkeypatch):
    from scenario.core.api import client, sdk_adapter

    class ClientReached(Exception):
        pass

    def selected(key, secret, **kwargs):
        assert (key, secret) == ("selected-key", "selected-secret")
        assert kwargs["project_id"] == ((project or "").strip() or None)
        raise ClientReached

    def selected_sdk(credentials, **kwargs):
        assert kwargs["online"]()
        selected(credentials.api_key, credentials.api_secret, **kwargs)

    monkeypatch.setattr(client, "ScenarioClient", selected)
    monkeypatch.setattr(sdk_adapter, "SDKAdapter", selected_sdk)
    monkeypatch.setenv("SCENARIO_TEST_API_KEY", "selected-key")
    monkeypatch.setenv("SCENARIO_TEST_API_SECRET", "selected-secret")
    if project is None:
        monkeypatch.delenv("SCENARIO_TEST_PROJECT_ID", raising=False)
    else:
        monkeypatch.setenv("SCENARIO_TEST_PROJECT_ID", project)
    monkeypatch.setenv("SCENARIO_SMOKE", "1")
    argv = [script] if script == "tools/record_fixtures.py" else [script, "synthetic-image.png"]
    monkeypatch.setattr("sys.argv", argv)
    monkeypatch.setenv("SCENARIO_API_KEY", "unrelated-key")
    monkeypatch.setenv("SCENARIO_API_SECRET", "unrelated-secret")
    with pytest.raises(ClientReached):
        runpy.run_path(str(ROOT / script), run_name="__main__")


@pytest.mark.parametrize("script", sorted((ROOT / "tests/smoke").glob("*.py")))
def test_smokes_require_opt_in_before_reading_credentials(script, monkeypatch):
    monkeypatch.delenv("SCENARIO_SMOKE", raising=False)
    with pytest.raises(SystemExit, match="set SCENARIO_SMOKE=1"):
        runpy.run_path(str(script), run_name="__main__")


def test_schema_cache_isolated_by_selected_scope(tmp_path, monkeypatch):
    from scenario.core.config import Credentials
    from tools import audit_payloads
    from tools.dev_config import LiveSettings

    monkeypatch.setattr(audit_payloads, "CACHE", tmp_path)
    monkeypatch.setattr(audit_payloads.time, "sleep", lambda _: None)

    class Client:
        def __init__(self, label):
            self.label = label
            self.calls = 0

        def get(self, path):
            self.calls += 1
            return {"model": {"name": self.label}}

    settings = [
        (LiveSettings(Credentials("key", "secret")), "https://one.invalid"),
        (LiveSettings(Credentials("key", "secret"), "project"), "https://one.invalid"),
        (LiveSettings(Credentials("other", "secret"), "project"), "https://one.invalid"),
        (LiveSettings(Credentials("key", "rotated"), "project"), "https://one.invalid"),
        (LiveSettings(Credentials("key", "secret"), "project"), "https://two.invalid"),
    ]
    for index, (selected, base_url) in enumerate(settings):
        client = Client(str(index))
        cache_dir = audit_payloads.schema_cache_dir(selected, base_url)
        for _ in range(2):
            assert audit_payloads.fetch(client, "model_x", cache_dir) == (
                {"name": str(index)},
                None,
            )
        assert client.calls == 1
