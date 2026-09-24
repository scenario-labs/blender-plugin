# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatible tool entry points retain exact artifacts and verified download paths."""

import importlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def tools(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return tuple(
        importlib.import_module(name) for name in ("fetch_blender", "build", "test_blender")
    )


@pytest.mark.parametrize(
    ("version", "platform", "filename"),
    [
        ("4.2.23", "linux-x64", "blender-4.2.23-linux-x64.tar.xz"),
        ("5.0.1", "linux-x64", "blender-5.0.1-linux-x64.tar.xz"),
        ("5.1.2", "windows-x64", "blender-5.1.2-windows-x64.zip"),
        ("5.2.1", "macos-arm64", "blender-5.2.1-macos-arm64.dmg"),
    ],
)
def test_public_release_helpers_share_official_urls(tools, version, platform, filename):
    fetch, _, _ = tools
    series = f"Blender{version.rsplit('.', 1)[0]}"
    assert fetch.series(version) == series
    assert fetch.url_for(version, platform_name=platform) == (
        f"https://download.blender.org/release/{series}/{filename}",
        f"https://download.blender.org/release/{series}/blender-{version}.sha256",
    )
    assert fetch.url_for("4.2.23")[0].endswith("blender-4.2.23-linux-x64.tar.xz")


@pytest.mark.parametrize("version", ["5.0", "5.0.1/other", "../5.0.1"])
def test_invalid_release_cannot_construct_download_urls(tools, version):
    fetch, _, _ = tools
    with pytest.raises(ValueError, match="full Blender version"):
        fetch.url_for(version)


@pytest.mark.parametrize("version_args", [["5.0.1"], ["--version", "5.0.1"]])
@pytest.mark.parametrize("destination", ["--dest", "--cache"])
def test_fetch_cli_aliases_call_the_same_verified_engine(
    tools, tmp_path, monkeypatch, version_args, destination
):
    fetch, _, _ = tools
    calls = []
    monkeypatch.setattr(fetch.platform, "system", lambda: "Linux")
    monkeypatch.setattr(fetch.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(fetch, "fetch", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(
        sys, "argv", ["fetch_blender.py", *version_args, destination, str(tmp_path)]
    )
    assert fetch.main() == 0
    assert calls == [(("5.0.1", tmp_path, None), {"platform_name": "linux-x64"})]


@pytest.mark.parametrize("args", [[], ["5.0.1", "--version", "5.1.2"]])
def test_fetch_missing_or_ambiguous_version_is_usage_error(tools, monkeypatch, args):
    fetch, _, _ = tools
    monkeypatch.setattr(sys, "argv", ["fetch_blender.py", *args])
    monkeypatch.setattr(fetch, "fetch", lambda *args, **kwargs: pytest.fail("must not download"))
    with pytest.raises(SystemExit) as error:
        fetch.main()
    assert error.value.code == 2


@pytest.mark.parametrize("repository", ["none", "default", "explicit"])
def test_repository_cli_accepts_optional_directory_without_changing_default(
    tools, tmp_path, monkeypatch, repository
):
    _, build, _ = tools
    output = tmp_path / "output"
    custom = tmp_path / "chosen repository"
    session = build.Session(Path("blender"), tmp_path / "artifacts")
    steps = []
    monkeypatch.setattr(build, "Session", lambda *args: session)
    monkeypatch.setattr(build, "find_blender", lambda _: Path("blender"))
    monkeypatch.setattr(session, "step", lambda *args: steps.append(args))

    def built(session, destination):
        assert destination == output
        destination.mkdir()
        candidate = destination / "scenario-0.9.9.zip"
        candidate.write_bytes(b"validated build fixture")
        return candidate

    monkeypatch.setattr(build, "build", built)
    extra = {"none": [], "default": ["--repo"], "explicit": ["--repo", str(custom)]}[repository]
    monkeypatch.setattr(sys, "argv", ["build.py", "--output", str(output), *extra])
    assert build.main() == 0
    if repository == "none":
        assert steps == []
    else:
        expected = output / "repo" if repository == "default" else custom
        assert (expected / "scenario-0.9.9.zip").read_bytes() == b"validated build fixture"
        assert steps == [
            (
                "repository",
                [
                    "--command",
                    "extension",
                    "server-generate",
                    "--repo-dir",
                    str(expected),
                    "--html",
                ],
            )
        ]
    assert not session.profile.exists()


def checkout(runner, monkeypatch, root, *, identity="scenario", version="0.9.9"):
    (root / "scenario").mkdir()
    (root / "dist").mkdir()
    (root / "scenario/blender_manifest.toml").write_text(
        f'id = "{identity}"\nversion = "{version}"\n'
    )
    monkeypatch.setattr(runner, "ROOT", root)
    return root / "dist/scenario-0.9.9.zip"


def test_no_build_selects_exact_manifest_filename_and_keeps_fresh_semantics(
    tools, tmp_path, monkeypatch
):
    _, _, runner = tools
    expected = checkout(runner, monkeypatch, tmp_path)
    expected.write_bytes(b"candidate selected for validation")
    (expected.parent / "scenario-99.0.0.zip").write_bytes(b"newer unrelated archive")
    monkeypatch.setattr(sys, "argv", ["test_blender.py", "--no-build", "--fresh"])

    def run(args):
        assert args.zip == expected
        assert args.no_build and args.fresh
        return 0

    monkeypatch.setattr(runner, "run", run)
    assert runner.main() == 0


def test_no_build_does_not_fall_back_to_another_archive(tools, tmp_path, monkeypatch, capsys):
    _, _, runner = tools
    expected = checkout(runner, monkeypatch, tmp_path)
    (expected.parent / "scenario-99.0.0.zip").write_bytes(b"stale")
    monkeypatch.setattr(sys, "argv", ["test_blender.py", "--no-build"])
    monkeypatch.setattr(runner, "run", lambda args: pytest.fail("must not start Blender"))
    assert runner.main() == 1
    assert "run make build first or use --zip PATH" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("identity", "version"), [("../scenario", "0.9.9"), ("scenario", "../0.9.9"), ("scenario", "")]
)
def test_no_build_rejects_invalid_manifest_path_components(
    tools, tmp_path, monkeypatch, identity, version
):
    _, _, runner = tools
    checkout(runner, monkeypatch, tmp_path, identity=identity, version=version)
    with pytest.raises(ValueError, match="valid extension id and version"):
        runner.existing_manifest_zip()


def test_explicit_zip_and_no_build_are_unambiguous_modes(tools, monkeypatch):
    _, _, runner = tools
    monkeypatch.setattr(sys, "argv", ["test_blender.py", "--no-build", "--zip", "candidate.zip"])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2


@pytest.mark.parametrize(
    ("identity", "version", "expected_exit"),
    [("scenario", "0.9.9", 7), ("scenario", "1.0.0", 1), ("other", "0.9.9", 1)],
)
def test_no_build_checks_copied_identity_and_still_requires_zip_validation(
    tools, tmp_path, monkeypatch, identity, version, expected_exit
):
    _, _, runner = tools
    candidate = checkout(runner, monkeypatch, tmp_path)
    for file in (tmp_path / "LICENSE", tmp_path / "scenario/LICENSE"):
        file.write_text("fixture licence")
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr(
            "blender_manifest.toml",
            f'id="{identity}"\nversion="{version}"\nblender_version_min="5.0.0"\n',
        )
        archive.writestr("LICENSE", "fixture licence")
        archive.writestr("__init__.py", "# fixture")
    monkeypatch.setattr(runner, "find_blender", lambda _: Path("blender"))
    monkeypatch.setattr(runner, "normal_profile_root", lambda: tmp_path / "normal")
    validated = []
    monkeypatch.setattr(runner, "validate_bundle", lambda candidate: validated.append(candidate))
    monkeypatch.setattr(runner, "prepare_source", lambda *args: pytest.fail("must not rebuild"))
    steps = []

    def step(binary, command, **kwargs):
        steps.append(kwargs["name"])
        if kwargs["name"] == "probe":
            log = tmp_path / "probe.log"
            log.write_text('SCENARIO_ENV={"blender":"5.0.1","version":[5,0,1]}')
            return log
        assert kwargs["name"] == "validate"
        raise subprocess.CalledProcessError(7, "invalid candidate fixture")

    monkeypatch.setattr(runner, "run_step", step)
    args = SimpleNamespace(
        blender=None,
        artifacts=tmp_path / "artifacts",
        suite="baseline",
        timeout=2,
        keep_profile=False,
        expected_version=None,
        zip=candidate,
        no_build=True,
    )
    assert runner.run(args) == expected_exit
    assert steps == (["probe", "validate"] if expected_exit == 7 else ["probe"])
    assert bool(validated) == (expected_exit == 7)
    report = json.loads(next(args.artifacts.glob("run-*/result.json")).read_text())
    assert report["status"] == "failed"
    if expected_exit == 1:
        assert (
            "version does not match" in report["error"] or "different extension" in report["error"]
        )
