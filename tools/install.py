# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install and enable an exact ZIP in a new isolated development profile."""

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from blender_env import find_blender, inspect_zip, sha256, verify_installed
from build import Session, arguments, build, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    arguments(parser)
    parser.add_argument("--zip", type=Path, help="Existing ZIP; otherwise build the current source")
    parser.add_argument("--launch", action="store_true", help="Open Blender using this new profile")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        session = Session(find_blender(args.blender), args.artifacts, args.timeout)
        if args.zip:
            candidate = session.directory / "candidate.zip"
            shutil.copyfile(args.zip, candidate)
            manifest = validate(session, candidate)
        else:
            candidate = build(session, session.directory / "dist")
            manifest, _ = inspect_zip(candidate)
        digest = sha256(candidate)
        session.step(
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
        installed = session.profile / "extensions/user_default" / manifest["id"]
        verify_installed(candidate, installed)
        if sha256(candidate) != digest:
            raise ValueError("Candidate ZIP changed during installation")
        (session.directory / "result.json").write_text(
            json.dumps(
                {
                    "zip": str(candidate),
                    "sha256": digest,
                    "profile": str(session.profile),
                    "installed": str(installed),
                },
                indent=2,
            )
            + "\n"
        )
        print(f"Installed {candidate}\nIsolated profile: {session.profile}")
        print("Use --launch to open the installed extension in its isolated profile.")
        if args.launch:
            # Keep the profile and temporary directory for the GUI's entire lifetime.
            return subprocess.call([str(session.binary)], cwd=session.directory, env=session.env)
        return 0
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 128 - error.returncode
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print(f"Install failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
