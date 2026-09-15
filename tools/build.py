# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build and validate an exact extension ZIP using a fresh Blender profile."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from blender_env import ROOT, find_blender, inspect_zip, isolated_environment, run_step, sha256
from wheel_bundle import prepare_source, validate_bundle


class Session:
    """Own only this invocation's profile; retain logs and failed profiles."""

    def __init__(self, binary, artifacts, timeout=300, *, prefix="tools-"):
        self.binary = binary
        artifacts.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix=prefix, dir=artifacts)).resolve()
        self.profile = self.directory / "profile"
        self.temporary = self.directory / "tmp"
        self.profile.mkdir()
        self.temporary.mkdir()
        self.env = isolated_environment(self.profile, self.temporary)
        self.timeout = timeout
        print(f"Artifacts: {self.directory}", flush=True)

    def step(self, name, args):
        return run_step(
            self.binary,
            args,
            env=self.env,
            directory=self.directory,
            name=name,
            timeout=self.timeout,
        )

    def cleanup(self):
        shutil.rmtree(self.profile)
        shutil.rmtree(self.temporary)


def validate(session, candidate):
    manifest, files = inspect_zip(candidate)
    expected = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())
    if manifest["id"] != expected["id"]:
        raise ValueError("Candidate ZIP is for a different extension")
    if (ROOT / "LICENSE").read_bytes() != (ROOT / "scenario/LICENSE").read_bytes():
        raise ValueError("Root and package licenses differ")
    if files["LICENSE"] != sha256(ROOT / "LICENSE"):
        raise ValueError("Candidate ZIP does not contain the repository GPL text")
    validate_bundle(candidate)
    session.step("validate", ["--command", "extension", "validate", str(candidate)])
    return manifest


def build(session, output):
    manifest = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())
    candidate = session.directory / f"{manifest['id']}-{manifest['version']}.zip"
    source = prepare_source(ROOT / "scenario", session.temporary / "source")
    session.step(
        "build",
        [
            "--command",
            "extension",
            "build",
            "--source-dir",
            str(source),
            "--output-filepath",
            str(candidate),
        ],
    )
    validate(session, candidate)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / candidate.name
    shutil.copyfile(candidate, destination)
    return destination


def arguments(parser):
    parser.add_argument(
        "--blender", help="Executable path or command; defaults to BLENDER/discovery"
    )
    parser.add_argument("--artifacts", type=Path, default=ROOT / ".blender-profile")
    parser.add_argument("--timeout", type=float, default=300, help="Seconds per Blender process")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    arguments(parser)
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="ZIP output directory")
    parser.add_argument("--repo", action="store_true", help="Also generate OUTPUT/repo/index.json")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        session = Session(find_blender(args.blender), args.artifacts, args.timeout)
        candidate = build(session, args.output)
        if args.repo:
            repository = args.output.resolve() / "repo"
            repository.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, repository / candidate.name)
            session.step(
                "repository",
                [
                    "--command",
                    "extension",
                    "server-generate",
                    "--repo-dir",
                    str(repository),
                    "--html",
                ],
            )
        (session.directory / "result.json").write_text(
            json.dumps({"zip": str(candidate), "sha256": sha256(candidate)}, indent=2) + "\n"
        )
        session.cleanup()
        print(f"Built {candidate}")
        return 0
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 128 - error.returncode
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
