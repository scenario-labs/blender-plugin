# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The live command requires explicit credentials and exposes only read/dry-run calls."""

from types import SimpleNamespace

import pytest

from tools import check_sdk


@pytest.mark.parametrize("project", [None, "fixture-project"])
def test_command_selects_test_credentials_and_passes_optional_project(
    monkeypatch, tmp_path, capsys, project
):
    monkeypatch.setenv("SCENARIO_TEST_API_KEY", "fixture-key")
    monkeypatch.setenv("SCENARIO_TEST_API_SECRET", "fixture-secret")
    monkeypatch.setenv("SCENARIO_TEST_PROJECT_ID", project or "")
    events = []

    class Client:
        def __init__(self, credentials, *, project_id, online):
            assert credentials.api_key == "fixture-key"
            assert credentials.api_secret == "fixture-secret"
            assert project_id == project and online()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append("closed")

        def models(self):
            return [{"id": "fixture"}]

        def model(self, identifier):
            assert identifier == "fixture"
            return {"id": identifier}

        def estimate_model(self, model, parameters):
            events.append("estimate")
            assert parameters == {"prompt": "test"}
            return SimpleNamespace(cost="0.125")

    monkeypatch.setattr(check_sdk, "SDKAdapter", Client)
    path = tmp_path / "parameters.json"
    path.write_text('{"prompt":"test"}')
    assert check_sdk.main(["--model", "fixture", "--parameters", str(path)]) == 0
    output = capsys.readouterr().out
    assert "1 models" in output and "0.125 CU" in output
    assert "fixture" not in output
    assert events == ["estimate", "closed"]


def test_command_rejects_missing_credentials_before_client_creation(monkeypatch):
    monkeypatch.delenv("SCENARIO_TEST_API_KEY", raising=False)
    monkeypatch.delenv("SCENARIO_TEST_API_SECRET", raising=False)

    def unexpected(*args, **kwargs):
        pytest.fail("Client constructed without explicit test credentials")

    monkeypatch.setattr(check_sdk, "SDKAdapter", unexpected)
    with pytest.raises(SystemExit, match="no test credentials"):
        check_sdk.main([])


def test_command_rejects_unpaired_estimate_arguments():
    with pytest.raises(SystemExit) as error:
        check_sdk.main(["--model", "fixture"])
    assert error.value.code == 2
