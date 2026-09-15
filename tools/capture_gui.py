# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture an installed extension in a fresh offline GUI; retain PNG and ZIP evidence."""

import argparse
import datetime
import json
import math
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from blender_env import (
    ROOT,
    find_blender,
    inspect_zip,
    normal_profile_root,
    profile_snapshot,
    sha256,
    verify_installed,
)
from build import Session, build, validate

PREPARE = (
    "import bpy,json; "
    "bpy.ops.wm.save_as_mainfile(filepath='fixture.blend'); "
    "print('CAPTURE_VERSION='+json.dumps(list(bpy.app.version)))"
)


def capture(args):
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    session = Session(
        find_blender(args.blender),
        args.output,
        args.timeout,
        prefix=f"{stamp}-{args.view}-{args.lane}-",
    )
    normal = normal_profile_root()
    before = profile_snapshot(normal)
    report = {"status": "failed", "view": args.view, "lane": args.lane, "fixture": args.fixture}
    report["label"] = args.label
    try:
        log = session.step(
            "prepare",
            ["--offline-mode", "--background", "--python-exit-code", "1", "--python-expr", PREPARE],
        )
        version = next(
            json.loads(line.removeprefix("CAPTURE_VERSION="))
            for line in log.read_text().splitlines()
            if line.startswith("CAPTURE_VERSION=")
        )
        if args.zip:
            candidate = session.directory / "candidate.zip"
            shutil.copyfile(args.zip, candidate)
            manifest = validate(session, candidate)
        else:
            candidate = build(session, session.directory / "dist")
            manifest, _ = inspect_zip(candidate)
        minimum = tuple(int(part) for part in manifest["blender_version_min"].split("."))
        if tuple(version) < minimum:
            raise ValueError("Blender is below the candidate ZIP minimum")
        digest = sha256(candidate)
        report.update(zip_sha256=digest, extension_version=manifest["version"])
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
        session.env["SCENARIO_GUI_PROBE"] = "1"
        session.step(
            "capture",
            [
                "--offline-mode",
                "--python-exit-code",
                "1",
                str(session.directory / "fixture.blend"),
                "--python",
                str(ROOT / "tools/capture_gui_scene.py"),
                "--",
                str(session.directory),
                str(installed),
                args.view,
                args.lane,
                str(args.delay),
                args.fixture,
            ],
        )
        evidence = json.loads((session.directory / "gui.json").read_text())
        if evidence.get("status") != "captured":
            raise ValueError("GUI did not confirm a successful capture")
        if evidence["blender_version"] != version or evidence["online_access"] is not False:
            raise ValueError("GUI runtime differs from the offline preparation")
        png = session.directory / "plugin.png"
        if not png.is_file() or png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Missing PNG capture")
        verify_installed(candidate, installed)
        if sha256(candidate) != digest:
            raise ValueError("Candidate ZIP changed during capture")
        report.update(evidence, png_sha256=sha256(png), status="captured")
        if profile_snapshot(normal) != before:
            raise ValueError("Normal Blender profile changed during capture")
        report["normal_profile_unchanged"] = True
        session.cleanup()
        print(f"Captured: {png}\nInspect the image before claiming visual acceptance.")
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        zipfile.BadZipFile,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        report["status"] = "failed"
        report["error"] = str(error)
        print(f"Capture failed: {error}", file=sys.stderr)
        return 1
    finally:
        (session.directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--blender", help="Executable path or command; defaults to BLENDER/discovery"
    )
    parser.add_argument("--timeout", type=float, default=60, help="Seconds per Blender process")
    parser.add_argument("--zip", type=Path, help="Exact ZIP; otherwise build current source")
    parser.add_argument(
        "--label", default="", help="Optional milestone/commit label for the report"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "workdir/screenshots",
        help="Parent directory for unique capture folders (default: workdir/screenshots)",
    )
    parser.add_argument("--view", choices=("sidebar", "composer"), default="sidebar")
    parser.add_argument("--lane", choices=("image", "video", "audio", "3d"), default="image")
    parser.add_argument(
        "--fixture",
        choices=("empty", "form"),
        default="empty",
        help="Signed-out UI or synthetic offline catalog/form (no real account)",
    )
    parser.add_argument(
        "--delay", type=float, default=8, help="Seconds before capture (at least 4)"
    )
    args = parser.parse_args()
    if not math.isfinite(args.delay) or args.delay < 4:
        parser.error("--delay must be finite and at least 4 seconds")
    if not math.isfinite(args.timeout) or args.timeout <= args.delay:
        parser.error("--timeout must be finite and greater than --delay")
    return capture(args)


if __name__ == "__main__":
    sys.exit(main())
