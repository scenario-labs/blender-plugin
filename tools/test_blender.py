# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build, install and test an exact extension ZIP in a new disposable Blender profile."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from blender_env import (
    ROOT,
    find_blender,
    inspect_zip,
    isolated_environment,
    normal_profile_root,
    profile_snapshot,
    sha256,
)

PROBE = "import bpy,json,platform,sys; print('SCENARIO_ENV='+json.dumps(dict(blender=bpy.app.version_string,version=list(bpy.app.version),python=sys.version,os=platform.platform())))"


def run_step(binary, args, *, env, directory, name, timeout):
    log = directory / f"{name}.log"
    print(f"{name}: {log}", flush=True)
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(
            [str(binary), *args],
            cwd=directory,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, name)
    return log


def run(args):
    binary = find_blender(args.blender)
    args.artifacts.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="run-", dir=args.artifacts)).resolve()
    profile = directory / "profile"
    temporary = directory / "tmp"
    profile.mkdir()
    temporary.mkdir()
    (directory / "runner.json").write_text(json.dumps({"profile": str(profile)}))
    env = isolated_environment(profile, temporary)
    normal_profile = normal_profile_root()
    before = profile_snapshot(normal_profile)
    report = {"status": "failed", "binary": str(binary), "suite": args.suite}
    print(f"Artifacts: {directory}", flush=True)
    try:

        def step(name, command):
            return run_step(
                binary, command, env=env, directory=directory, name=name, timeout=args.timeout
            )

        probe_log = step(
            "probe",
            [
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "--python-expr",
                PROBE,
            ],
        )
        environment = next(
            json.loads(line.removeprefix("SCENARIO_ENV="))
            for line in probe_log.read_text().splitlines()
            if line.startswith("SCENARIO_ENV=")
        )
        report.update(environment)
        print(json.dumps(environment), flush=True)
        manifest = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())
        minimum = tuple(int(part) for part in manifest["blender_version_min"].split("."))
        if tuple(environment["version"]) < minimum:
            raise ValueError(
                f"Blender {environment['blender']} is below the extension minimum {manifest['blender_version_min']}"
            )
        if args.expected_version and environment["blender"] != args.expected_version:
            raise ValueError("Blender binary does not match --expected-version")
        candidate = directory / f"{manifest['id']}-{manifest['version']}.zip"
        if args.zip:
            shutil.copyfile(args.zip, candidate)
        else:
            step(
                "build",
                [
                    "--command",
                    "extension",
                    "build",
                    "--source-dir",
                    str(ROOT / "scenario"),
                    "--output-filepath",
                    str(candidate),
                ],
            )
        candidate_manifest, candidate_files = inspect_zip(candidate)
        if candidate_manifest["id"] != manifest["id"]:
            raise ValueError("Candidate ZIP is for a different extension")
        if (ROOT / "LICENSE").read_bytes() != (ROOT / "scenario/LICENSE").read_bytes():
            raise ValueError("Root and package licenses differ")
        if candidate_files["LICENSE"] != sha256(ROOT / "LICENSE"):
            raise ValueError("Candidate ZIP does not contain the repository GPL text")
        step("validate", ["--command", "extension", "validate", str(candidate)])
        report["zip_sha256"] = sha256(candidate)
        report["extension_version"] = candidate_manifest["version"]
        step(
            "install",
            [
                "--offline-mode",
                "--command",
                "extension",
                "install-file",
                "--repo",
                "user_default",
                "--enable",
                str(candidate),
            ],
        )
        step(
            "tests",
            [
                "--background",
                "--python-exit-code",
                "1",
                "--python",
                str(ROOT / "tests/blender/run_all.py"),
                "--",
                "--zip",
                str(candidate),
                "--sha256",
                report["zip_sha256"],
                "--suite",
                args.suite,
                "--report",
                str(directory / "tests.json"),
            ],
        )
        tests = json.loads((directory / "tests.json").read_text())
        if tests["zip_sha256"] != report["zip_sha256"] or not tests["success"]:
            raise ValueError("Missing or unsuccessful installed-package evidence")
        report["tests"] = tests
        if profile_snapshot(normal_profile) != before:
            raise ValueError("Normal Blender profile changed during the run")
        report["normal_profile_unchanged"] = True
        report["status"] = "passed"
        print(f"PASS: {tests['tests_run']} tests; ZIP SHA-256 {report['zip_sha256']}", flush=True)
        return 0
    except subprocess.CalledProcessError as error:
        report["error"] = f"{error.cmd} exited {error.returncode}"
        print(report["error"], file=sys.stderr)
        return error.returncode if error.returncode > 0 else 128 - error.returncode
    except (
        OSError,
        ValueError,
        StopIteration,
        KeyError,
        zipfile.BadZipFile,
        subprocess.TimeoutExpired,
    ) as error:
        report["error"] = str(error) or type(error).__name__
        print(f"FAIL: {report['error']}", file=sys.stderr)
        return 1
    finally:
        (directory / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        if report["status"] == "passed" and not args.keep_profile:
            shutil.rmtree(profile)
            shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--blender", help="Executable path or command; defaults to BLENDER, then discovery"
    )
    parser.add_argument("--expected-version", help="Require this exact Blender version (CI)")
    parser.add_argument(
        "--zip", type=Path, help="Test an existing ZIP instead of building the checkout"
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=ROOT / ".blender-profile",
        help="Parent for unique run directories containing logs, ZIP and JSON reports",
    )
    parser.add_argument("--suite", choices=("baseline", "all"), default="baseline")
    parser.add_argument(
        "--timeout", type=float, default=300, help="Maximum seconds per Blender process"
    )
    parser.add_argument(
        "--keep-profile",
        action="store_true",
        help="Keep the successful run's profile and temporary files too",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        return run(args)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    sys.exit(main())
