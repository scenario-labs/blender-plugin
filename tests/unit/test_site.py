# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Complete offline site snapshots retain exact releases and fail without partial output."""

import importlib
import json
import subprocess
from pathlib import Path

import pytest

from tests.unit.test_docs_html import PNG, TEMPLATE
from tests.unit.test_release_inventory import Releases
from tests.unit.test_repository import NativeSession, archive, inventory


@pytest.fixture
def builder(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return importlib.import_module("build_site")


@pytest.fixture
def inputs(builder, tmp_path):
    docs = tmp_path / "docs"
    (docs / "images").mkdir(parents=True)
    (docs / "images/panel.png").write_bytes(PNG)
    source = docs / "guide.md"
    source.write_text("# Guide\n\n## Install\n\n![The settings panel](images/panel.png)\n")
    template = docs / "template.html"
    template.write_text(TEMPLATE)
    manifest = tmp_path / "manifest.toml"
    # The guide version is independent of the retained release versions.
    manifest.write_text('id = "fixture"\nversion = "3.0.0"\n')
    repository = importlib.import_module("repository")
    archives = tmp_path / "archives"
    archives.mkdir()
    selected = inventory(
        repository,
        archives,
        [
            archive(archives, "old.zip"),
            archive(archives, "new.zip", version="2.0.0", minimum="5.1.0", maximum=None),
        ],
    )
    return {
        "inventory": selected,
        "output": tmp_path / "site",
        "source": source,
        "template": template,
        "manifest": manifest,
        "root": tmp_path,
    }


def files(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def test_complete_site_and_inventory_replay_preserve_exact_release_history(builder, inputs):
    originals = files(inputs["inventory"].parent)
    output = builder.build_site(NativeSession(), **inputs)
    assert set(files(output)) == {
        "index.html",
        "index.html.assets.json",
        "images/panel.png",
        "repo/index.html",
        "repo/index.json",
        "repo/inventory.json",
        "repo/old.zip",
        "repo/new.zip",
    }
    page = (output / "index.html").read_text()
    assert "<footer>3.0.0</footer>" in page
    assert 'src="images/panel.png"' in page and "data:image" not in page
    assert (output / "images/panel.png").read_bytes() == PNG
    index = json.loads((output / "repo/index.json").read_text())
    assert {row["version"] for row in index["data"]} == {"1.0.0", "2.0.0"}
    for row in index["data"]:
        path = output / "repo" / row["archive_url"]
        assert path.read_bytes() == originals[path.name]
        assert row["archive_url"] in (output / "repo/index.html").read_text()
    second = builder.build_site(
        NativeSession(),
        **{
            **inputs,
            "inventory": output / "repo/inventory.json",
            "output": output.with_name("two"),
        },
    )
    assert files(second) == files(output)
    inputs["source"].write_text("# Updated guide\n\nNo screenshot now.\n")
    third = builder.build_site(NativeSession(), **{**inputs, "output": output.with_name("three")})
    assert files(third / "repo") == files(output / "repo")
    assert not (third / "images").exists()
    assert files(inputs["inventory"].parent) == originals


def test_release_selector_feeds_site_without_drafts_or_losing_older_compatibility(builder, inputs):
    selector = importlib.import_module("release_inventory")
    releases = Releases(inputs["root"])
    _, old = releases.add("1.0.0", maximum="5.1.0")
    row, new = releases.add("2.0.0", minimum="5.1.0")
    releases.rows.append({**row, "tag_name": "blender-plugin-v9.0.0", "draft": True, "assets": []})
    selected = releases.prepare(selector, inputs["root"] / "selected")
    inputs["manifest"].write_text('id = "scenario"\nversion = "3.0.0"\n')
    output = builder.build_site(NativeSession(), **{**inputs, "inventory": selected})
    assert {path.name for path in (output / "repo").glob("*.zip")} == {old.name, new.name}
    for path in (old, new):
        assert (output / "repo" / path.name).read_bytes() == path.read_bytes()


@pytest.mark.parametrize("problem", ["missing", "hash", "size", "empty", "identity"])
def test_invalid_inventory_leaves_no_site(builder, inputs, problem):
    selected = inputs["inventory"]
    value = json.loads(selected.read_text())
    if problem == "missing":
        (selected.parent / "old.zip").unlink()
    elif problem == "hash":
        value["archives"][0]["sha256"] = "0" * 64
    elif problem == "size":
        value["archives"][0]["size"] += 1
    elif problem == "empty":
        value["archives"] = []
    else:
        value["extension_id"] = "other"
    selected.write_text(json.dumps(value))
    before = files(selected.parent)
    with pytest.raises(ValueError):
        builder.build_site(NativeSession(), **inputs)
    assert not inputs["output"].exists()
    assert not list(inputs["root"].glob(".site-*"))
    assert files(selected.parent) == before


@pytest.mark.parametrize("problem", ["image", "alt", "template", "reserved", "reserved-case"])
def test_renderer_failure_leaves_no_site_or_native_calls(builder, inputs, problem):
    if problem == "image":
        (inputs["source"].parent / "images/panel.png").unlink()
    elif problem == "alt":
        inputs["source"].write_text("![](images/panel.png)")
    elif problem == "template":
        inputs["template"].write_text(TEMPLATE + "{{unknown}}")
    else:
        directory = inputs["source"].parent / ("REPO" if problem == "reserved-case" else "repo")
        directory.mkdir()
        (directory / "image.png").write_bytes(PNG)
        inputs["source"].write_text(f"![Repository screenshot]({directory.name}/image.png)")
    session = NativeSession()
    with pytest.raises(ValueError):
        builder.build_site(session, **inputs)
    assert session.calls == []
    assert not inputs["output"].exists()
    assert not list(inputs["root"].glob(".site-*"))


@pytest.mark.parametrize("problem", ["validation", "index", "zip"])
def test_native_failure_never_exposes_partial_site(builder, inputs, problem):
    def mutate(index, directory):
        if problem == "index":
            index["data"][0]["blender_version_min"] = "4.0.0"
        elif problem == "zip":
            (directory / "old.zip").write_bytes(b"tampered")

    before = files(inputs["inventory"].parent)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        builder.build_site(NativeSession(mutate, problem == "validation"), **inputs)
    assert not inputs["output"].exists()
    assert not list(inputs["root"].glob(".site-*"))
    assert files(inputs["inventory"].parent) == before


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling"])
def test_existing_outputs_are_preserved(builder, inputs, kind):
    output = inputs["output"]
    if kind == "directory":
        output.mkdir()
        (output / "keep").write_text("previous output")
    elif kind == "file":
        output.write_text("previous output")
    else:
        output.symlink_to(inputs["source"] if kind == "symlink" else output.with_name("absent"))
    session = NativeSession()
    with pytest.raises(ValueError, match="already exists"):
        builder.build_site(session, **inputs)
    assert session.calls == []
    if kind == "directory":
        assert (output / "keep").read_text() == "previous output"
    elif kind == "file":
        assert output.read_text() == "previous output"
    else:
        assert output.is_symlink()


def test_output_appearing_during_generation_is_preserved(builder, inputs):
    def appear(_index, _directory):
        inputs["output"].mkdir()
        (inputs["output"] / "keep").write_text("concurrent output")

    with pytest.raises(ValueError, match="already exists"):
        builder.build_site(NativeSession(appear), **inputs)
    assert files(inputs["output"]) == {"keep": b"concurrent output"}
    assert not list(inputs["root"].glob(".site-*"))


@pytest.mark.parametrize("failure", [None, "validation", "timeout", "inventory"])
def test_cli_runs_builders_and_preserves_failure_status(
    builder, inputs, monkeypatch, capsys, failure
):
    session = NativeSession(fail_validation=failure == "validation")
    cleaned = []
    session.cleanup = lambda: cleaned.append(True)
    monkeypatch.setattr(builder, "find_blender", lambda value: value)
    monkeypatch.setattr(builder, "Session", lambda *_: session)
    if failure == "timeout":

        def timeout(*_):
            raise subprocess.TimeoutExpired("blender", 1)

        session.step = timeout
    elif failure == "inventory":
        inputs["inventory"].write_text("invalid")
    args = ["--blender", "fixture-blender", "--artifacts", str(inputs["root"] / "logs")]
    for name in ("inventory", "output", "source", "template", "manifest"):
        args.extend(["--" + name, str(inputs[name])])
    assert builder.main(args) == (0 if failure is None else 1)
    assert cleaned == ([True] if failure is None else [])
    assert inputs["output"].exists() == (failure is None)
    captured = capsys.readouterr()
    assert ("Verified site:" in captured.out) == (failure is None)
    if failure in {"timeout", "inventory"}:
        assert "Site build failed:" in captured.err


def test_cli_rejects_artifacts_inside_site_before_creating_a_profile(builder, inputs):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(builder, "Session", lambda *_: pytest.fail("Created a profile"))
        assert (
            builder.main(
                [
                    "--inventory",
                    str(inputs["inventory"]),
                    "--output",
                    str(inputs["output"]),
                    "--artifacts",
                    str(inputs["output"] / "logs"),
                ]
            )
            == 1
        )
    assert not inputs["output"].exists()


def test_make_site_uses_locked_environment_and_forwards_arguments():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "make",
            "-n",
            "site",
            "UV=uv",
            "SITE_ARGS=--inventory selected/inventory.json --output dist/site",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == (
        "uv run --locked --no-env-file python tools/build_site.py "
        "--inventory selected/inventory.json --output dist/site"
    )
