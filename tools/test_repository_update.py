# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test native updates on loopback with synthetic fixtures or two exact Scenario ZIPs."""

import argparse
import contextlib
import http.server
import json
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
import zipfile
from pathlib import Path
from types import SimpleNamespace

from blender_env import (
    ROOT,
    find_blender,
    inspect_zip,
    normal_profile_root,
    profile_snapshot,
    sha256,
    verify_installed,
)
from build import Session, arguments
from repository import generate, version, write_json
from test_blender import PROBE

REPO = "update_fixture"


def package_artifact(directory, source):
    """Copy an exact caller-selected package; never rewrite its version or contents."""
    if not source.is_file() or source.is_symlink():
        raise ValueError("Package ZIP must be a regular file")
    manifest, files = inspect_zip(source)
    if manifest["id"] != "scenario" or "core/jobs/store.py" not in files:
        raise ValueError("Use an adopted Scenario package with durable job storage")
    version(manifest["version"])
    directory.mkdir()
    path = directory / f"scenario-{manifest['version']}.zip"
    shutil.copyfile(source, path)
    inventory = write_inventory(path, manifest["version"])
    return path, inventory, manifest["version"]


def write_inventory(path, package_version):
    inventory = path.parent / "inventory.json"
    write_json(
        inventory,
        {
            "schema_version": 1,
            "extension_id": "scenario",
            "archives": [
                {
                    "file": path.name,
                    "version": package_version,
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                }
            ],
        },
    )
    return inventory


def store_schema(path):
    """Read a package's declared job-store schema without importing its code."""
    with zipfile.ZipFile(path) as archive:
        source = archive.read("core/jobs/store.py").decode("utf-8")
    match = re.search(r"(?m)^_VERSION = ([1-9][0-9]*)$", source)
    if match is None:
        raise ValueError("Package job storage declares no schema version")
    return int(match.group(1))


def fixture_predecessor(directory, package):
    """Make a clearly synthetic predecessor; only version metadata may differ.

    `package` is the candidate by default, or an exact earlier package whose code
    shares the candidate's version number (an unreleased predecessor commit).
    """
    manifest, _ = inspect_zip(package)
    current = manifest["version"]
    if version(current) <= (0, 0, 0):
        raise ValueError("Test predecessor requires a package newer than 0.0.0")
    directory.mkdir()
    path = directory / "scenario-0.0.0.zip"
    replacements = {"blender_manifest.toml": "version", "__init__.py": "__version__"}
    changed = set()
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(path, "w") as destination:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename in replacements:
                name = replacements[info.filename]
                content, count = re.subn(
                    rb"(?m)^("
                    + name.encode()
                    + rb"\s*=\s*)([\"'])"
                    + re.escape(current.encode())
                    + rb"\2",
                    rb'\g<1>"0.0.0"',
                    content,
                )
                if count != 1:
                    raise ValueError("Test predecessor requires one matching version declaration")
                changed.add(info.filename)
            destination.writestr(info, content)
    if changed != set(replacements):
        raise ValueError("Test predecessor is missing package version metadata")
    return path, write_inventory(path, "0.0.0"), "0.0.0"


def fixture(directory, version):
    """Create test-only artifacts, never modify a released or checkout package."""
    directory.mkdir()
    path = directory / f"scenario-{version}.zip"
    manifest = (
        "# SPDX-FileCopyrightText: 2026 Scenario Inc.\n"
        "# SPDX-License-Identifier: GPL-3.0-or-later\n"
        'schema_version = "1.0.0"\nid = "scenario"\nname = "Scenario update fixture"\n'
        'tagline = "Synthetic native updater regression"\nmaintainer = "Scenario Inc."\n'
        'type = "add-on"\nlicense = ["SPDX:GPL-3.0-or-later"]\n'
        'blender_version_min = "5.0.0"\n'
        f'version = "{version}"\n'
    )
    source = (
        "# SPDX-FileCopyrightText: 2026 Scenario Inc.\n"
        "# SPDX-License-Identifier: GPL-3.0-or-later\n"
        "import bpy\n"
        f"VERSION = {version!r}\n"
        "def register():\n"
        "    bpy.types.WindowManager.scenario_update_fixture_version = VERSION\n"
        "def unregister():\n"
        "    del bpy.types.WindowManager.scenario_update_fixture_version\n"
    )
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in {
            "blender_manifest.toml": manifest.encode(),
            "__init__.py": source.encode(),
            "LICENSE": (ROOT / "LICENSE").read_bytes(),
        }.items():
            archive.writestr(zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)), content)
    inventory = write_inventory(path, version)
    return path, inventory


class RepositoryHandler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_args):
        pass

    def do_GET(self):
        # Only generated public fixture files may be served; no directory traversal/listings.
        path = urllib.parse.urlsplit(self.path).path
        if path not in self.server.allowed_paths:
            self.send_error(404)
            return
        source = self.server.repository / path.removeprefix("/")
        if not source.is_file():
            self.send_error(404)
            return
        content = source.read_bytes()
        self.server.requests.append(path)
        self.send_response(200)
        self.send_header("Content-Length", str(len(content)))
        self.send_header(
            "Content-Type", "application/json" if path.endswith(".json") else "application/zip"
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


@contextlib.contextmanager
def serve(repository, archives=("scenario-1.0.0.zip", "scenario-2.0.0.zip")):
    if any(Path(name).name != name or not name.endswith(".zip") for name in archives):
        raise ValueError("Serve only explicit archive basenames")
    with http.server.HTTPServer(("127.0.0.1", 0), RepositoryHandler) as server:
        server.repository = repository
        server.allowed_paths = frozenset({"/index.json", *("/" + name for name in archives)})
        server.requests = []
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        try:
            yield server, f"http://127.0.0.1:{server.server_port}/index.json"
        finally:
            server.shutdown()
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("Loopback repository server did not stop")


def run(args):
    previous, candidate = getattr(args, "previous_zip", None), getattr(args, "candidate_zip", None)
    test_predecessor = getattr(args, "test_predecessor", False)
    if test_predecessor and candidate is None:
        raise ValueError("--test-predecessor requires --candidate-zip")
    if not test_predecessor and bool(previous) != bool(candidate):
        raise ValueError("Provide both --previous-zip and --candidate-zip")
    package_mode = candidate is not None
    normal_profile = normal_profile_root().resolve()
    if args.artifacts.resolve().is_relative_to(normal_profile):
        raise ValueError("Artifacts must be outside the normal Blender profile")
    before = profile_snapshot(normal_profile)
    session = Session(find_blender(args.blender), args.artifacts, args.timeout, prefix="update-")
    # A user's proxy must never redirect the loopback fixture to an external service.
    session.env = {
        key: value for key, value in session.env.items() if not key.upper().endswith("_PROXY")
    }
    session.env["NO_PROXY"] = "127.0.0.1,localhost"
    session.env["no_proxy"] = "127.0.0.1,localhost"
    report = {
        "status": "failed",
        "fixture": "scenario-package" if package_mode else "synthetic",
        "repository": REPO,
        "test_predecessor": test_predecessor,
    }
    if test_predecessor:
        report["predecessor_code"] = "previous-zip" if previous is not None else "candidate"
    server = None
    write_json(session.directory / "repository-update.json", {"profile": str(session.profile)})
    try:
        probe = session.step(
            "probe",
            [
                "--offline-mode",
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
            for line in probe.read_text().splitlines()
            if line.startswith("SCENARIO_ENV=")
        )
        if args.expected_version and tuple(environment["version"]) != tuple(
            map(int, args.expected_version.split("."))
        ):
            raise ValueError("Blender binary does not match --expected-version")
        report.update(environment)
        before_version, after_version = "1.0.0", "2.0.0"
        if package_mode:
            second, second_inventory, after_version = package_artifact(
                session.directory / "second", candidate
            )
            if test_predecessor:
                code = second
                if previous is not None:
                    # Same-version predecessor code; only its version metadata changes.
                    code, _, _ = package_artifact(session.directory / "previous", previous)
                    report["previous_sha256"] = sha256(code)
                first, first_inventory, before_version = fixture_predecessor(
                    session.directory / "first", code
                )
            else:
                first, first_inventory, before_version = package_artifact(
                    session.directory / "first", previous
                )
            if version(after_version) <= version(before_version):
                raise ValueError("Candidate version must be newer than the previous package")
            schemas = {"before": store_schema(first), "after": store_schema(second)}
            if schemas["after"] < schemas["before"]:
                raise ValueError("Candidate job storage is older than the previous package")
        else:
            first, first_inventory = fixture(session.directory / "first", before_version)
            second, second_inventory = fixture(session.directory / "second", after_version)

        def native_repository(label, inventory):
            commands = SimpleNamespace(
                step=lambda name, args: session.step(f"{label}-{name}", args)
            )
            return generate(commands, inventory, session.directory / f"repository-{label}")

        first_repo = native_repository("first", first_inventory)
        second_repo = native_repository("second", second_inventory)
        installed = session.profile / "extensions" / REPO / "scenario"
        with serve(first_repo, (first.name, second.name)) as (server, url):
            # All saved repository changes belong to this invocation's disposable profile.
            session.step(
                "configure",
                [
                    "--offline-mode",
                    "--command",
                    "extension",
                    "repo-add",
                    REPO,
                    "--name",
                    "Scenario update fixture",
                    "--url",
                    url,
                    "--clear-all",
                ],
            )
            session.step(
                "install",
                [
                    "--online-mode",
                    "--command",
                    "extension",
                    "install",
                    "--sync",
                    "--enable",
                    f"{REPO}.scenario",
                ],
            )
            verify_installed(first, installed)
            server.repository = second_repo
            evidence = session.directory / "update.json"
            probe_script = "package_update.py" if package_mode else "repository_update.py"
            extra = ["--before", before_version, "--after", after_version] if package_mode else []
            session.step(
                "update",
                [
                    "--online-mode",
                    "--background",
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(ROOT / "tests/blender" / probe_script),
                    "--",
                    "--url",
                    url,
                    "--report",
                    str(evidence),
                    *extra,
                ],
            )
            report["update"] = json.loads(evidence.read_text())
            expected = {"before": before_version, "after": after_version, "enabled": True}
            if package_mode:
                expected.update(
                    state_preserved=True,
                    scene_preserved=True,
                    project_scope_preserved=True,
                    workflow_references_preserved=(
                        json.loads((session.directory / "expected-state.json").read_text())[
                            "workflow"
                        ]
                        is not None
                    ),
                    service_requests=0,
                    store_schema=schemas,
                    schema_10_state=(
                        "before-update"
                        if schemas["before"] >= 10
                        else "after-upgrade"
                        if schemas["after"] >= 10
                        else "unavailable"
                    ),
                )
            if report["update"] != expected:
                raise ValueError("Missing native update and enabled-state evidence")
            verify_installed(second, installed)
            if not {"/index.json", "/" + first.name, "/" + second.name}.issubset(server.requests):
                raise ValueError("Native updater did not fetch both exact fixture archives")
            report["requests"] = server.requests
            if package_mode:
                restart = session.directory / "restart.json"
                session.step(
                    "restart",
                    [
                        "--offline-mode",
                        "--background",
                        "--python-exit-code",
                        "1",
                        "--python",
                        str(ROOT / "tests/blender" / probe_script),
                        "--",
                        "--url",
                        url,
                        "--report",
                        str(restart),
                        *extra,
                        "--restart",
                    ],
                )
                report["restart"] = json.loads(restart.read_text())
                if report["restart"] != expected:
                    raise ValueError("Package state did not survive an offline Blender restart")
                verify_installed(second, installed)
        report["server_stopped"] = True
        if profile_snapshot(normal_profile) != before:
            raise ValueError("Normal Blender profile changed during the run")
        report["normal_profile_unchanged"] = True
        report["archives"] = {first.name: sha256(first), second.name: sha256(second)}
        session.cleanup()
        report["profile_removed"] = not session.profile.exists() and not session.temporary.exists()
        report["status"] = "passed"
        print(
            "PASS: native install/update preserved enabled state and exact archive bytes"
            + ("; Scenario state and scene survived update and restart" if package_mode else ""),
            flush=True,
        )
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        RuntimeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as error:
        report["error"] = str(error) or type(error).__name__
        print(f"Native update failed: {report['error']}", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            report["server_stopped"] = server.socket.fileno() == -1
        write_json(session.directory / "result.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    arguments(parser)
    parser.add_argument("--expected-version", help="Require this exact Blender version (CI)")
    parser.add_argument("--previous-zip", type=Path, help="Exact previously adopted Scenario ZIP")
    parser.add_argument("--candidate-zip", type=Path, help="Exact newer Scenario ZIP to accept")
    parser.add_argument(
        "--test-predecessor",
        action="store_true",
        help=(
            "Use test-only version 0.0.0 metadata with the --previous-zip code, or the candidate "
            "code without it; not release-pair acceptance"
        ),
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        return run(args)
    except (OSError, ValueError) as error:
        print(f"Native update failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
