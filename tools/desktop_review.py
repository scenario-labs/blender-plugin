# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch an exact ZIP for offline, isolated macOS desktop interaction review."""

import argparse
import hashlib
import json
import math
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

from blender_env import (
    ROOT,
    find_blender,
    normal_profile_root,
    profile_snapshot,
    sha256,
    verify_installed,
)
from build import Session, validate

SCENE_SCRIPT = Path(__file__).with_name("desktop_review_scene.py")


def application_identity(binary, artifacts):
    """Keep approval identity stable across runs, independent of ZIP/profile bytes."""
    scope = json.dumps([str(binary.resolve()), str(artifacts.resolve())])
    return hashlib.sha256(scope.encode("utf-8")).hexdigest()[:12]


def lock_application(artifacts, identity):
    """Prevent two supervised windows from sharing an attachment identity."""
    import fcntl  # The desktop runner is macOS-only; keep other tool imports portable.

    artifacts.mkdir(parents=True, exist_ok=True)
    lock = (artifacts / f".application-{identity}.lock").open("a+b")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        lock.close()
        raise ValueError(
            "A desktop review already uses this app identity; finish it or use another --artifacts directory"
        ) from error
    except BaseException:
        lock.close()
        raise
    # Do not unlink: another process may already have opened the same inode.
    return lock


def review_environment(session):
    """Use an allowlist, including profile overrides for Launch Services relaunches."""
    env = {
        "PATH": os.defpath,
        "HOME": str(session.directory / "home"),
        "XDG_CONFIG_HOME": str(session.directory / "home/.config"),
        "BLENDER_USER_RESOURCES": str(session.profile),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SCENARIO_GUI_PROBE": "1",
    }
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(session.temporary)
    for key, folder in (
        ("BLENDER_USER_CONFIG", "config"),
        ("BLENDER_USER_SCRIPTS", "scripts"),
        ("BLENDER_USER_EXTENSIONS", "extensions"),
        ("BLENDER_USER_DATAFILES", "datafiles"),
    ):
        env[key] = str(session.profile / folder)
        (session.profile / folder).mkdir()
    (session.directory / "home/.config").mkdir(parents=True)
    return env


def copy_application(binary, directory, env, identity):
    """Keep the real executable as CFBundleExecutable; wrappers break attachment."""
    source = binary.parent.parent.parent
    if source.suffix != ".app" or binary.parent != source / "Contents/MacOS":
        raise ValueError("--blender must select an executable inside a macOS .app")
    info_path = source / "Contents/Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    if info.get("CFBundleExecutable") != binary.name:
        raise ValueError("Selected executable does not match the application bundle")
    target = directory / f"ScenarioReview-{identity}.app"
    # Plain copy also works when source and artifacts are on different volumes.
    shutil.copytree(source, target, symlinks=True)
    name = f"ScenarioReview-{identity}"
    (target / "Contents/MacOS" / binary.name).rename(target / "Contents/MacOS" / name)
    info.update(
        CFBundleExecutable=name,
        CFBundleIdentifier=f"com.scenario.desktop-review.{identity}",
        CFBundleName=name,
        CFBundleDisplayName=name,
        LSEnvironment=env,
    )
    # The temporary app must not claim the user's .blend file associations.
    info.pop("CFBundleDocumentTypes", None)
    info.pop("UTExportedTypeDeclarations", None)
    (target / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(target)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return target / "Contents/MacOS" / name, info["CFBundleIdentifier"]


def stop_child(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)


def run_review(args):
    session = None
    before = None
    child = None
    application_lock = None
    report = {"status": "failed", "interaction_acceptance": "not_assessed"}
    normal = normal_profile_root().resolve()
    try:
        if platform.system() != "Darwin":
            raise ValueError("Desktop review currently supports macOS only")
        if args.artifacts.resolve().is_relative_to(normal):
            raise ValueError("Artifacts cannot be inside the normal Blender profile")
        binary = find_blender(args.blender)
        if args.artifacts.resolve().is_relative_to(binary.parent.parent.parent):
            raise ValueError("Artifacts cannot be inside the source Blender application")
        identity = application_identity(binary, args.artifacts)
        application_lock = lock_application(args.artifacts, identity)
        before = profile_snapshot(normal)
        session = Session(None, args.artifacts, args.timeout, prefix="desktop-")
        session.env = review_environment(session)
        session.binary, bundle_id = copy_application(
            binary, session.directory, session.env, identity
        )
        report.update(bundle_id=bundle_id, app=str(session.binary.parent.parent.parent))
        # --offline-mode makes this preference read-only. Save it in a factory
        # background process before installing/loading the extension instead.
        session.step(
            "offline-preferences",
            [
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "--python-expr",
                "import bpy; "
                "bpy.context.preferences.system.use_online_access=False; "
                "bpy.ops.wm.save_userpref()",
            ],
        )
        candidate = session.directory / "candidate.zip"
        shutil.copyfile(args.zip, candidate)
        manifest = validate(session, candidate)
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
        # Copy the fixture so this run does not depend on later checkout edits.
        shutil.copyfile(SCENE_SCRIPT, session.directory / "scene.py")
        fixture = session.directory / f"Scenario-Review-{uuid.uuid4().hex[:12]}.blend"
        config = {
            "profile": str(session.profile),
            "installed": str(installed),
            "fixture": str(fixture),
            "duration": args.duration,
        }
        (session.directory / "review.json").write_text(json.dumps(config, indent=2) + "\n")
        scene_args = ["--python", str(session.directory / "scene.py"), "--", str(session.directory)]
        session.step(
            "prepare",
            ["--background", "--offline-mode", "--python-exit-code", "1", *scene_args, "prepare"],
        )
        if profile_snapshot(normal) != before:
            raise ValueError("Normal Blender profile changed during preparation")
        with (session.directory / "desktop.log").open("w") as log:
            child = subprocess.Popen(
                [
                    str(session.binary),
                    "--offline-mode",
                    "--disable-autoexec",
                    "--python-exit-code",
                    "1",
                    str(fixture),
                    *scene_args,
                    "observe",
                ],
                env=session.env,
                cwd=session.directory,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            report.update(status="running", pid=child.pid, fixture=str(fixture))
            write_report(session, report)
            print(
                f"Attach to {bundle_id}\nExpected window: {fixture.name}\nPID: {child.pid}",
                flush=True,
            )
            print(
                "Verify ready.json before input. Quit Blender when done; this does not certify UI acceptance.",
                flush=True,
            )
            try:
                code = child.wait(timeout=args.duration + 30)
            finally:
                stop_child(child)
        report["exit_code"] = code
        ready = json.loads((session.directory / "ready.json").read_text())
        if code != 0 or ready["pid"] != child.pid or ready["online_access"] is not False:
            raise ValueError("The identified offline review process did not finish successfully")
        observed = json.loads((session.directory / "observed.json").read_text())
        if (
            observed["pid"] != child.pid
            or observed["online_access"] is not False
            or observed["network_violations"]
        ):
            raise ValueError("Review observation violated the offline process contract")
        verify_installed(candidate, installed)
        if sha256(candidate) != digest:
            raise ValueError("Candidate ZIP changed during review")
        report.update(status="finished", blender_version=ready["blender_version"])
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        report.update(status="failed", error=str(error))
        print(f"Desktop review failed: {error}", file=sys.stderr)
    except KeyboardInterrupt:
        report.update(status="interrupted")
    finally:
        if child is not None:
            try:
                stop_child(child)
            except (OSError, subprocess.SubprocessError) as error:
                report.update(status="failed", cleanup_error=str(error))
                print(f"Desktop review cleanup failed: {error}", file=sys.stderr)
        if application_lock is not None:
            application_lock.close()
        if before is not None:
            report["normal_profile_unchanged"] = profile_snapshot(normal) == before
            if not report["normal_profile_unchanged"]:
                report["status"] = "failed"
        if session is not None:
            write_report(session, report)
            print(f"Report: {session.directory / 'report.json'}", flush=True)
    return 0 if report["status"] == "finished" else 1


def write_report(session, report):
    (session.directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", help="Blender executable inside the source macOS .app")
    parser.add_argument("--zip", required=True, type=Path, help="Exact trusted extension ZIP")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "workdir/desktop-review")
    parser.add_argument("--timeout", type=float, default=300, help="Seconds per setup process")
    parser.add_argument(
        "--duration", type=float, default=900, help="Maximum GUI lifetime in seconds"
    )
    args = parser.parse_args()
    if any(not math.isfinite(v) or v <= 0 for v in (args.timeout, args.duration)):
        parser.error("Timeout and duration must be finite and positive")
    return run_review(args)


if __name__ == "__main__":
    sys.exit(main())
