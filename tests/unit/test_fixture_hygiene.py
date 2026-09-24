# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixture privacy checks use structural rules, never real account identifiers."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tools import record_fixtures as recorder

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def fields(data):
    if isinstance(data, dict):
        for key, value in data.items():
            yield key, value
            yield from fields(value)
    elif isinstance(data, list):
        for value in data:
            yield None, value
            yield from fields(value)


def documents():
    for path in sorted(FIXTURES.rglob("*.json")):
        yield path.relative_to(FIXTURES), json.loads(path.read_text(encoding="utf-8"))


def test_committed_account_fields_use_placeholders():
    for path, data in documents():
        for key, value in fields(data):
            if key in recorder.PLACEHOLDERS and isinstance(value, str):
                if value != recorder.PLACEHOLDERS[key]:
                    pytest.fail(f"{path}: scrub account field {key} before committing")


def test_committed_strings_have_no_signed_urls():
    for path, data in documents():
        for _, value in fields(data):
            if recorder.is_signed_url(value):
                pytest.fail(f"{path}: scrub signed URL before committing")


def test_committed_scrub_is_idempotent():
    for path, data in documents():
        if recorder.scrub(data) != data:
            pytest.fail(f"{path}: run tools/record_fixtures.py --scrub-existing")


def test_scrub_preserves_semantics_and_input():
    data = {
        "model": {
            "id": "model_fixture",
            **{key: "synthetic-account" for key in recorder.PLACEHOLDERS},
            "exampleAssetIds": ["asset_fixture"],
            "collectionIds": ["collection_fixture"],
            "inputs": [{"name": "ownerId", "type": "string"}],
            "url": "https://cdn.example/a.png?Key-Pair-Id=K&Policy=P&Signature=S",  # secrets-allow: synthetic fixture
            "docs": "https://example.com/page?tab=1",
            "job": {"id": "job_fixture", "status": "success"},
            "schema": {"ownerId": {"type": "string"}, "teamId": None, "createdBy": 42},
        }
    }
    original = copy.deepcopy(data)
    clean = recorder.scrub(data)
    expected = copy.deepcopy(data)
    expected["model"].update(recorder.PLACEHOLDERS)
    expected["model"]["url"] = recorder.SIGNED_URL_PLACEHOLDER
    assert clean == expected
    assert data == original


def test_mutating_scrubbed_containers_cannot_change_input():
    data = {"models": [{"exampleAssetIds": ["asset_fixture"]}]}
    clean = recorder.scrub(data)
    clean["models"][0]["exampleAssetIds"].append("asset_other")
    assert data == {"models": [{"exampleAssetIds": ["asset_fixture"]}]}


@pytest.mark.parametrize(
    "url",
    [
        "https://cdn.example/a?Key-Pair-Id=K",  # secrets-allow: synthetic fixture
        "http://cdn.example/a?Policy=P",
        "https://cdn.example/a?Signature=S",
        "HTTPS://cdn.example/a?X-Amz-Signature=S",  # secrets-allow: synthetic fixture
        "https://cdn.example/a?X-Amz-Credential=C",  # secrets-allow: synthetic fixture
        "https://cdn.example/a?%53ignature=S",
        "https://cdn.example/a?sIgNaTuRe=",
        "https://[invalid-host/a?Signature=S",
    ],
)
def test_signed_query_keys_are_redacted(url):
    assert recorder.is_signed_url(url)
    assert recorder.scrub([url]) == [recorder.SIGNED_URL_PLACEHOLDER]


@pytest.mark.parametrize(
    "value",
    [
        None,
        3,
        "Signature=S",
        "https://example.com/Signature=S",
        "https://example.com/?tab=1#Signature=S",
        "https://example.com/#fragment?Signature=S",
        "https://example.com/?description=Signature%3DS",
        "https://example.com/?notSignature=S",
    ],
)
def test_plain_values_and_documentation_links_are_preserved(value):
    assert not recorder.is_signed_url(value)
    assert recorder.scrub(value) == value


@pytest.mark.parametrize("indent", [" ", "  ", "\t"])
def test_offline_scrub_preserves_layout_and_needs_no_credentials(
    tmp_path, monkeypatch, capsys, indent
):
    compact = tmp_path / "compact.json"
    pretty = tmp_path / "pretty.json"
    untouched = tmp_path / "untouched.json"
    compact.write_text('{"ownerId":"synthetic-account"}', encoding="utf-8")
    pretty.write_text("{\n" + indent + '"authorId": "synthetic-account"\n}\n', encoding="utf-8")
    untouched.write_text('{ "future": null }', encoding="utf-8")
    monkeypatch.setattr(recorder, "FIXTURES", tmp_path)
    settings = Mock(side_effect=AssertionError("must not request credentials"))
    client = Mock(side_effect=AssertionError("must not construct a client"))
    monkeypatch.setattr(recorder, "live_settings", settings)
    monkeypatch.setattr(recorder, "ScenarioClient", client)
    recorder.main(["--scrub-existing"])
    assert "\n" not in compact.read_text()
    assert (
        pretty.read_text()
        == json.dumps({"authorId": recorder.PLACEHOLDERS["authorId"]}, indent=indent) + "\n"
    )
    assert untouched.read_text() == '{ "future": null }'
    assert capsys.readouterr().out.splitlines() == ["scrubbed compact.json", "scrubbed pretty.json"]
    before = {path: path.read_bytes() for path in tmp_path.iterdir()}
    recorder.main(["--scrub-existing"])
    assert capsys.readouterr().out == ""
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == before
    settings.assert_not_called()
    client.assert_not_called()


def test_malformed_inventory_fails_before_writing_or_echoing_contents(tmp_path):
    good = tmp_path / "a.json"
    good.write_text('{"ownerId":"synthetic-account"}', encoding="utf-8")
    bad = tmp_path / "z.json"
    bad.write_text('{"private": "https://cdn.example/?Signature=SECRET"', encoding="utf-8")
    before = good.read_bytes()
    with pytest.raises(ValueError, match=r"^invalid fixture JSON: z\.json$"):
        recorder.scrub_existing(tmp_path)
    assert good.read_bytes() == before


def test_recording_writes_are_scrubbed_without_live_requests(tmp_path, monkeypatch, capsys):
    model = {
        "model": {
            "id": "model_fixture",
            "userId": "synthetic-account",
            "url": "https://cdn.example/a?Signature=S",
        }
    }
    page = {"models": [{"id": "model_first", "ownerId": "synthetic-account"}]}
    client = Mock()
    client.get.side_effect = [model, page, {"models": [{"id": "model_next"}]}]
    monkeypatch.setattr(recorder, "ROOT", tmp_path)
    monkeypatch.setattr(recorder, "FIXTURES", tmp_path / "tests" / "fixtures")
    monkeypatch.setattr(recorder, "MODEL_IDS", ["model_fixture"])
    monkeypatch.setattr(recorder, "ScenarioClient", Mock(return_value=client))
    monkeypatch.setattr(
        recorder,
        "live_settings",
        lambda: SimpleNamespace(
            credentials=SimpleNamespace(key="fake", secret="fake"), project_id=None
        ),
    )
    recorder.main([])
    assert json.loads(
        (recorder.FIXTURES / "models" / "model_fixture.json").read_text()
    ) == recorder.scrub(model)
    assert json.loads((recorder.FIXTURES / "models_list_page1.json").read_text()) == recorder.scrub(
        page
    )
    assert "synthetic-account" not in capsys.readouterr().out


@pytest.mark.parametrize("argv,code", [(["--help"], 0), (["--scrbu-existing"], 2)])
def test_cli_help_and_invalid_arguments_do_not_request_credentials(monkeypatch, argv, code):
    settings = Mock(side_effect=AssertionError("must not request credentials"))
    monkeypatch.setattr(recorder, "live_settings", settings)
    with pytest.raises(SystemExit) as error:
        recorder.main(argv)
    assert error.value.code == code
    settings.assert_not_called()
