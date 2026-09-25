# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the audit CLI with real SDK transport and explicit offline snapshots."""

import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from scenario.core.api.sdk_adapter import SDKAdapter
from tools import audit_payloads as audit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/models"


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch):
    for name in (
        "SCENARIO_TEST_API_KEY",
        "SCENARIO_TEST_API_SECRET",
        "SCENARIO_TEST_PROJECT_ID",
        "SCHEMA_CACHE",
        "SCENARIO_API_BASE",
    ):
        monkeypatch.delenv(name, raising=False)


def test_offline_wrapped_fixtures_need_no_configuration_or_client(tmp_path, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("offline must not use credentials or SDK"))
    monkeypatch.setattr(audit, "live_settings", forbidden)
    report = tmp_path / "audit.md"
    assert (
        audit.run(
            [
                "--offline",
                "--cache",
                str(FIXTURES),
                "--models",
                "model_rodin-hyper3d-bang",
                "model_meshy-7-retexture",
                "--fail-on",
                "HIGH",
                "--report",
                str(report),
            ],
            client_factory=forbidden,
        )
        == 0
    )
    text = report.read_text()
    assert text.startswith("# Payload audit\n")
    assert "2 schemas checked; 0 fetch/schema failures; 0 findings" in text
    forbidden.assert_not_called()


def test_missing_credentials_return_usage_error_without_constructing_client(tmp_path, capsys):
    forbidden = Mock(side_effect=AssertionError("no SDK without credentials"))
    assert (
        audit.run(["--cache", str(tmp_path), "--models", "model_fixture"], client_factory=forbidden)
        == 2
    )
    assert "SCENARIO_TEST_API_KEY and SCENARIO_TEST_API_SECRET" in capsys.readouterr().err
    forbidden.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_invalid_sdk_base_url_is_a_sanitized_configuration_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SCENARIO_TEST_API_KEY", "fixture-key")
    monkeypatch.setenv("SCENARIO_TEST_API_SECRET", "fixture-secret")
    monkeypatch.setenv("SCENARIO_API_BASE", "https://service.example.invalid:private-port/v1")
    assert audit.run(["--cache", str(tmp_path), "--models", "model_fixture"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Invalid SDK audit configuration\n"
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def sdk(monkeypatch):
    monkeypatch.setenv("SCENARIO_TEST_API_KEY", "fixture-key")
    monkeypatch.setenv("SCENARIO_TEST_API_SECRET", "fixture-secret")
    monkeypatch.setenv("SCENARIO_TEST_PROJECT_ID", "fixture-project")
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    monkeypatch.setenv("SCENARIO_BASE_URL", "https://ambient.invalid")
    requests, clients = [], []

    def factory(response):
        def create(settings, base_url):
            assert base_url == audit.API_URL

            def handle(request):
                requests.append(request)
                assert request.method == "GET"
                assert (
                    request.headers["Authorization"] == "Basic Zml4dHVyZS1rZXk6Zml4dHVyZS1zZWNyZXQ="
                )
                assert dict(request.url.params) == {"projectId": "fixture-project"}
                return response(request)

            client = SDKAdapter(
                audit.Credentials(settings.credentials.key, settings.credentials.secret),
                project_id=settings.project_id,
                online=lambda: True,
                base_url="https://service.example.invalid/v1",
                transport=httpx.MockTransport(handle),
            )
            clients.append(client)
            return client

        return create

    return factory, requests, clients


@pytest.mark.parametrize("status", [404, 500])
def test_failed_sdk_read_is_once_sanitized_and_sets_threshold_exit(tmp_path, sdk, capsys, status):
    factory, requests, clients = sdk
    client_factory = factory(lambda _: httpx.Response(status, json={"error": "private-response"}))
    assert (
        audit.run(
            ["--cache", str(tmp_path), "--models", "model_missing", "--fail-on", "HIGH"],
            client_factory=client_factory,
        )
        == 1
    )
    assert len(requests) == 1 and requests[0].url.path == "/v1/models/model_missing"
    assert all(client._closed for client in clients)
    text = capsys.readouterr().out
    assert "## Fetch failures" in text
    assert "private-response" not in text
    assert "fixture-project" not in text
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("first_suffix,last_suffix", [("", ""), ("/", ""), ("", "/"), ("///", "/")])
def test_live_reads_cache_and_close_sdk_then_cache_hit_avoids_client(
    tmp_path, sdk, capsys, monkeypatch, first_suffix, last_suffix
):
    factory, requests, clients = sdk
    model = json.loads((FIXTURES / "model_meshy-7-retexture.json").read_text())["model"]
    argv = ["--cache", str(tmp_path), "--models", model["id"], "--fail-on", "HIGH"]
    monkeypatch.setenv("SCENARIO_API_BASE", audit.API_URL + first_suffix)
    assert (
        audit.run(
            argv, client_factory=factory(lambda _: httpx.Response(200, json={"model": model}))
        )
        == 0
    )
    assert len(requests) == 1 and all(client._closed for client in clients)
    files = list(tmp_path.glob("*/*.json"))
    assert len(files) == 1 and json.loads(files[0].read_text()) == model
    forbidden = Mock(side_effect=AssertionError("cached audit must not create SDK"))
    monkeypatch.setenv("SCENARIO_API_BASE", audit.API_URL + last_suffix)
    assert audit.run(argv, client_factory=forbidden) == 0
    forbidden.assert_not_called()
    assert "fixture-key" not in capsys.readouterr().out


@pytest.mark.parametrize("threshold,expected", [(None, 0), ("HIGH", 1), ("MED", 1), ("LOW", 1)])
def test_empty_schema_is_high_finding(tmp_path, capsys, threshold, expected):
    (tmp_path / "model_empty.json").write_text('{"id":"model_empty","inputs":[]}')
    args = ["--offline", "--cache", str(tmp_path), "--models", "model_empty"]
    if threshold:
        args += ["--fail-on", threshold]
    assert audit.run(args) == expected
    assert "**HIGH** `empty-schema`" in capsys.readouterr().out


@pytest.mark.parametrize(
    "content",
    [
        None,
        "{",
        "[]",
        '{"id":"model_other"}',
        '{"model":null}',
        '{"id":"model_fixture","inputs":[null]}',
    ],
)
def test_missing_malformed_or_wrong_identity_cache_is_reported_without_live_fallback(
    tmp_path, content, capsys
):
    if content is not None:
        (tmp_path / "model_fixture.json").write_text(content)
    forbidden = Mock(side_effect=AssertionError("offline failure cannot use SDK"))
    assert (
        audit.run(
            [
                "--offline",
                "--cache",
                str(tmp_path),
                "--models",
                "model_fixture",
                "--fail-on",
                "HIGH",
            ],
            client_factory=forbidden,
        )
        == 1
    )
    assert "1 fetch/schema failures" in capsys.readouterr().out
    forbidden.assert_not_called()


@pytest.mark.parametrize(
    "argv",
    [
        ["--offline"],
        ["--models", "../model_escape"],
        ["--models", "model_bad/slash"],
        ["--models", "model_bad?query"],
        ["--fail-on", "NONE"],
    ],
)
def test_invalid_usage_is_rejected_before_configuration(argv, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("invalid argv must not read settings"))
    monkeypatch.setattr(audit, "live_settings", forbidden)
    with pytest.raises(SystemExit) as error:
        audit.run(argv)
    assert error.value.code == 2
    forbidden.assert_not_called()


def test_unwritable_report_returns_two_without_traceback(tmp_path, capsys):
    assert (
        audit.run(
            [
                "--offline",
                "--cache",
                str(FIXTURES),
                "--models",
                "model_meshy-7-retexture",
                "--report",
                str(tmp_path / "absent/audit.md"),
            ]
        )
        == 2
    )
    assert capsys.readouterr().err == "Could not write the audit report\n"


def test_cache_symlink_is_not_followed_or_replaced(tmp_path, capsys):
    link = tmp_path / "model_fixture.json"
    link.symlink_to(tmp_path / "absent")
    assert (
        audit.run(
            [
                "--offline",
                "--cache",
                str(tmp_path),
                "--models",
                "model_fixture",
                "--fail-on",
                "HIGH",
            ]
        )
        == 1
    )
    assert "must not be a symlink" in capsys.readouterr().out
    assert link.is_symlink() and not (tmp_path / "absent").exists()


@pytest.mark.parametrize("threshold,expected", [("HIGH", 0), ("MED", 1), ("LOW", 1)])
def test_medium_finding_obeys_selected_threshold(tmp_path, capsys, threshold, expected):
    model = {
        "id": "model_two_images",
        "inputs": [
            {"name": name, "kind": "image", "type": "file", "required": True}
            for name in ("first", "second")
        ],
    }
    (tmp_path / "model_two_images.json").write_text(json.dumps(model))
    assert (
        audit.run(
            [
                "--offline",
                "--cache",
                str(tmp_path),
                "--models",
                "model_two_images",
                "--fail-on",
                threshold,
            ]
        )
        == expected
    )
    assert "**MED** `multiple-required-files`" in capsys.readouterr().out


def test_sdk_wrong_identity_is_never_cached(tmp_path, sdk, capsys):
    factory, requests, clients = sdk
    assert (
        audit.run(
            [
                "--cache",
                str(tmp_path),
                "--models",
                "model_fixture",
                "--fail-on",
                "HIGH",
            ],
            client_factory=factory(
                lambda _: httpx.Response(200, json={"model": {"id": "model_other"}})
            ),
        )
        == 1
    )
    assert len(requests) == 1 and all(client._closed for client in clients)
    assert list(tmp_path.iterdir()) == []
    assert "different identity" in capsys.readouterr().out


def test_report_only_fetch_failure_keeps_zero_exit(tmp_path, capsys):
    assert audit.run(["--offline", "--cache", str(tmp_path), "--models", "model_absent"]) == 0
    assert "1 fetch/schema failures" in capsys.readouterr().out


def test_signed_url_in_schema_label_is_not_reported(tmp_path, capsys):
    model = {
        "id": "model_url",
        "inputs": [
            {
                "name": "image",
                "kind": "image",
                "type": "file",
                "required": True,
                "description": "optional",
                "label": "https://cdn.example/a?Signature=private-value",
            }
        ],
    }
    (tmp_path / "model_url.json").write_text(json.dumps(model))
    assert (
        audit.run(
            ["--offline", "--cache", str(tmp_path), "--models", "model_url", "--fail-on", "HIGH"]
        )
        == 1
    )
    text = capsys.readouterr().out
    assert "conditional-required-file" in text and "[URL omitted]" in text
    assert "Signature" not in text and "private-value" not in text


def test_cache_publication_failure_leaves_no_partial_file(tmp_path, sdk, monkeypatch, capsys):
    factory, _, clients = sdk

    def fail_replace(*args):
        raise OSError("private-path")

    monkeypatch.setattr(audit.os, "replace", fail_replace)
    assert (
        audit.run(
            [
                "--cache",
                str(tmp_path),
                "--models",
                "model_fixture",
                "--fail-on",
                "HIGH",
            ],
            client_factory=factory(
                lambda _: httpx.Response(200, json={"model": {"id": "model_fixture"}})
            ),
        )
        == 1
    )
    assert not any(p.is_file() for p in tmp_path.rglob("*"))
    assert all(client._closed for client in clients)
    text = capsys.readouterr().out
    assert "could not store the model cache" in text and "private-path" not in text


def test_cache_cleanup_failure_preserves_sanitized_primary_error(
    tmp_path, sdk, monkeypatch, capsys
):
    factory, _, clients = sdk

    def fail(*args, **kwargs):
        raise OSError("private-path")

    monkeypatch.setattr(audit.os, "replace", fail)
    monkeypatch.setattr(Path, "unlink", fail)
    assert (
        audit.run(
            [
                "--cache",
                str(tmp_path),
                "--models",
                "model_fixture",
                "--fail-on",
                "HIGH",
            ],
            client_factory=factory(
                lambda _: httpx.Response(200, json={"model": {"id": "model_fixture"}})
            ),
        )
        == 1
    )
    assert not list(tmp_path.rglob("model_fixture.json"))
    assert all(client._closed for client in clients)
    captured = capsys.readouterr()
    assert "could not store the model cache" in captured.out
    assert "private-path" not in captured.out and captured.err == ""


def link_directory(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Host does not permit directory symlinks")


def live_scope(root):
    return audit.schema_cache_dir(audit.live_settings(), audit.API_URL, root)


@pytest.mark.parametrize("part", ["root", "scope"])
@pytest.mark.parametrize("selection", ["flag", "environment"])
def test_precreated_live_directory_symlink_is_rejected_before_cache_or_sdk(
    tmp_path, sdk, monkeypatch, capsys, part, selection
):
    root = tmp_path / "cache"
    target = tmp_path / "other-directory"
    target.mkdir(mode=0o700)
    if part == "root":
        link_directory(root, target)
        scope = live_scope(target)
        scope.mkdir(mode=0o700)
    else:
        root.mkdir(mode=0o700)
        link_directory(live_scope(root), target)
        scope = target
    cached = scope / "model_fixture.json"
    cached.write_text('{"id":"model_fixture","inputs":[]}')
    before = cached.read_bytes()
    forbidden = Mock(side_effect=AssertionError("unsafe directory reached SDK"))
    args = ["--models", "model_fixture"]
    if selection == "flag":
        args += ["--cache", str(root)]
    else:
        monkeypatch.setenv("SCHEMA_CACHE", str(root))
    assert audit.run(args, client_factory=forbidden) == 2
    forbidden.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "Unsafe or inaccessible live model cache\n"
    assert cached.read_bytes() == before


@pytest.mark.skipif(os.name != "posix", reason="POSIX directory owner/mode boundary")
@pytest.mark.parametrize("part", ["root", "scope"])
@pytest.mark.parametrize("mode", [0o755, 0o777])
def test_nonprivate_live_directories_are_rejected_without_chmod(tmp_path, sdk, capsys, part, mode):
    root = tmp_path / "cache"
    root.mkdir(mode=0o700)
    scope = live_scope(root)
    scope.mkdir(mode=0o700)
    bad = root if part == "root" else scope
    bad.chmod(mode)
    forbidden = Mock(side_effect=AssertionError("nonprivate cache reached SDK"))
    assert audit.run(["--cache", str(root)], client_factory=forbidden) == 2
    assert stat.S_IMODE(bad.stat().st_mode) == mode
    forbidden.assert_not_called()
    assert capsys.readouterr().err == "Unsafe or inaccessible live model cache\n"


@pytest.mark.skipif(os.name != "posix", reason="POSIX directory owner/mode boundary")
@pytest.mark.parametrize("part", ["root", "scope", "parent"])
def test_foreign_owned_live_directories_are_rejected_before_sdk(tmp_path, sdk, monkeypatch, part):
    parent = tmp_path / "parent"
    parent.mkdir(mode=0o700)
    root = parent / "cache"
    root.mkdir(mode=0o700)
    scope = live_scope(root)
    scope.mkdir(mode=0o700)
    bad = {"root": root, "scope": scope, "parent": parent}[part]
    original = Path.lstat

    def foreign_owner(path):
        info = original(path)
        if path == bad:
            return SimpleNamespace(st_mode=info.st_mode, st_uid=os.geteuid() + 1)
        return info

    monkeypatch.setattr(Path, "lstat", foreign_owner)
    forbidden = Mock(side_effect=AssertionError("foreign-owned cache reached SDK"))
    assert audit.run(["--cache", str(root)], client_factory=forbidden) == 2
    forbidden.assert_not_called()


@pytest.mark.skipif(os.name != "posix", reason="POSIX directory owner/mode boundary")
def test_shared_writable_parent_is_rejected_but_sticky_parent_accepts_owned_leaf(tmp_path, sdk):
    parent = tmp_path / "shared"
    parent.mkdir()
    parent.chmod(0o777)
    root = parent / "cache"
    forbidden = Mock(side_effect=AssertionError("untrusted parent reached SDK"))
    assert audit.run(["--cache", str(root)], client_factory=forbidden) == 2
    assert not root.exists()
    forbidden.assert_not_called()
    parent.chmod(0o1777)
    factory, requests, _ = sdk
    assert (
        audit.run(
            ["--cache", str(root), "--models", "model_fixture"],
            client_factory=factory(
                lambda _: httpx.Response(200, json={"model": {"id": "model_fixture"}})
            ),
        )
        == 0
    )
    assert len(requests) == 1
    assert stat.S_IMODE(root.stat().st_mode) == 0o700


@pytest.mark.parametrize("part", ["root", "scope"])
def test_reparse_live_directory_is_rejected_before_sdk(tmp_path, sdk, monkeypatch, part):
    root = tmp_path / "cache"
    root.mkdir(mode=0o700)
    scope = live_scope(root)
    scope.mkdir(mode=0o700)
    bad = root if part == "root" else scope
    original = Path.lstat

    def reparse(path):
        info = original(path)
        if path == bad:
            return SimpleNamespace(
                st_mode=info.st_mode, st_uid=info.st_uid, st_file_attributes=0x400
            )
        return info

    monkeypatch.setattr(Path, "lstat", reparse)
    forbidden = Mock(side_effect=AssertionError("reparse directory reached SDK"))
    assert audit.run(["--cache", str(root)], client_factory=forbidden) == 2
    forbidden.assert_not_called()


def test_trusted_parent_alias_is_canonicalized_and_persistent_cache_reused(tmp_path, sdk):
    target = tmp_path / "real-parent"
    target.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    link_directory(alias, target)
    root = alias / "cache"
    factory, requests, _ = sdk
    args = ["--cache", str(root), "--models", "model_fixture"]
    assert (
        audit.run(
            args,
            client_factory=factory(
                lambda _: httpx.Response(200, json={"model": {"id": "model_fixture"}})
            ),
        )
        == 0
    )
    assert len(requests) == 1
    assert len(list((target / "cache").glob("*/model_fixture.json"))) == 1
    forbidden = Mock(side_effect=AssertionError("cache hit must not construct SDK"))
    assert audit.run(args, client_factory=forbidden) == 0
    forbidden.assert_not_called()


@pytest.mark.parametrize("part", ["root", "scope"])
def test_live_directory_created_during_read_is_checked_before_publication(tmp_path, sdk, part):
    root = tmp_path / "cache"
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    if part == "scope":
        root.mkdir(mode=0o700)
    factory, requests, _ = sdk

    def response(_):
        link_directory(root if part == "root" else live_scope(root), other)
        return httpx.Response(200, json={"model": {"id": "model_fixture"}})

    assert (
        audit.run(
            ["--cache", str(root), "--models", "model_fixture", "--fail-on", "HIGH"],
            client_factory=factory(response),
        )
        == 1
    )
    assert len(requests) == 1 and list(other.iterdir()) == []


@pytest.mark.parametrize("status", [200, 500])
@pytest.mark.parametrize("empty_setting", [False, True])
def test_default_cache_is_unique_cleaned_and_ignores_predictable_precreation(
    tmp_path, sdk, monkeypatch, status, empty_setting
):
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    old = tmp_path / "scenario-schema-cache"
    link_directory(old, other)
    created = []
    original = audit.tempfile.TemporaryDirectory

    def temporary(**kwargs):
        directory = original(dir=tmp_path, **kwargs)
        created.append(Path(directory.name))
        return directory

    monkeypatch.setattr(audit.tempfile, "TemporaryDirectory", temporary)
    if empty_setting:
        monkeypatch.setenv("SCHEMA_CACHE", "")
    factory, requests, clients = sdk
    for _ in range(2):
        assert (
            audit.run(
                ["--models", "model_fixture"],
                client_factory=factory(
                    lambda _: httpx.Response(status, json={"model": {"id": "model_fixture"}})
                ),
            )
            == 0
        )
    assert len(requests) == 2 and all(client._closed for client in clients)
    assert len(set(created)) == 2 and all(not path.exists() for path in created)
    assert old.is_symlink() and list(other.iterdir()) == []
    assert set(tmp_path.iterdir()) == {old, other}


@pytest.mark.parametrize(
    "outcome,destination",
    [
        ("clean", "file"),
        ("clean", "stdout"),
        ("finding", "file"),
        ("fetch", "file"),
        ("config", "file"),
    ],
)
def test_default_cache_cleanup_failure_preserves_report_and_safe_exit(
    tmp_path, sdk, monkeypatch, capsys, outcome, destination
):
    factory, requests, clients = sdk
    original = audit.tempfile.TemporaryDirectory
    cleaned = []

    class FailingCleanup(original):
        def cleanup(self):
            assert all(client._closed for client in clients)
            super().cleanup()
            cleaned.append(self.name)
            raise OSError("private cleanup path and details")

    monkeypatch.setattr(
        audit.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: FailingCleanup(dir=tmp_path, **kwargs),
    )
    model = json.loads((FIXTURES / "model_meshy-7-retexture.json").read_text())["model"]
    if outcome == "finding":
        model = {"id": model["id"], "inputs": []}
    client_factory = factory(
        lambda _: httpx.Response(500 if outcome == "fetch" else 200, json={"model": model})
    )
    if outcome == "config":
        client_factory = Mock(side_effect=ValueError("private configuration details"))
    args = ["--models", model["id"], "--fail-on", "HIGH"]
    report = tmp_path / "report.md"
    if destination == "file":
        args += ["--report", str(report)]
    assert audit.run(args, client_factory=client_factory) == 2
    captured = capsys.readouterr()
    assert len(cleaned) == 1 and not Path(cleaned[0]).exists()
    assert len(requests) == (0 if outcome == "config" else 1)
    expected = "Could not remove the temporary model cache\n"
    if outcome == "config":
        assert not report.exists() and captured.out == ""
        assert captured.err == "Invalid SDK audit configuration\n" + expected
    else:
        text = report.read_text() if destination == "file" else captured.out
        assert text.startswith("# Payload audit\n")
        assert captured.err == expected
        if outcome == "fetch":
            assert "0 schemas checked; 1 fetch/schema failures" in text
            assert "SDK model read failed" in text
        elif outcome == "finding":
            assert "1 schemas checked; 0 fetch/schema failures" in text
            assert "**HIGH** `empty-schema`" in text
        else:
            assert "1 schemas checked; 0 fetch/schema failures; 0 findings" in text


def test_missing_persistent_parent_is_rejected_without_creating_it(tmp_path, sdk):
    root = tmp_path / "absent" / "cache"
    forbidden = Mock(side_effect=AssertionError("missing parent reached SDK"))
    assert audit.run(["--cache", str(root)], client_factory=forbidden) == 2
    forbidden.assert_not_called()
    assert not root.parent.exists()


def test_looping_live_cache_parent_is_sanitized_before_sdk(tmp_path, sdk, capsys):
    parent = tmp_path / "private-loop"
    link_directory(parent, parent)
    forbidden = Mock(side_effect=AssertionError("looping parent reached SDK"))
    assert audit.run(["--cache", str(parent / "cache")], client_factory=forbidden) == 2
    forbidden.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "Unsafe or inaccessible live model cache\n"


def test_offline_nonregular_entry_is_reported_without_reading_it(tmp_path, capsys):
    (tmp_path / "model_fixture.json").mkdir()
    assert (
        audit.run(
            [
                "--offline",
                "--cache",
                str(tmp_path),
                "--models",
                "model_fixture",
                "--fail-on",
                "HIGH",
            ]
        )
        == 1
    )
    assert "must be a regular file" in capsys.readouterr().out
