# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test Blender's native extension update against exact synthetic ZIPs on loopback."""

import argparse
import contextlib
import http.server
import json
import subprocess
import sys
import threading
import urllib.parse
import zipfile
from types import SimpleNamespace

from blender_env import (
    ROOT,
    find_blender,
    normal_profile_root,
    profile_snapshot,
    sha256,
    verify_installed,
)
from build import Session, arguments
from repository import generate, write_json
from test_blender import PROBE

REPO = "update_fixture"


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
    inventory = directory / "inventory.json"
    write_json(
        inventory,
        {
            "schema_version": 1,
            "extension_id": "scenario",
            "archives": [
                {
                    "file": path.name,
                    "version": version,
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                }
            ],
        },
    )
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
        if path not in {"/index.json", "/scenario-1.0.0.zip", "/scenario-2.0.0.zip"}:
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
def serve(repository):
    with http.server.HTTPServer(("127.0.0.1", 0), RepositoryHandler) as server:
        server.repository = repository
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
    report = {"status": "failed", "fixture": "synthetic", "repository": REPO}
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
        first, first_inventory = fixture(session.directory / "first", "1.0.0")
        second, second_inventory = fixture(session.directory / "second", "2.0.0")

        def native_repository(label, inventory):
            commands = SimpleNamespace(
                step=lambda name, args: session.step(f"{label}-{name}", args)
            )
            return generate(commands, inventory, session.directory / f"repository-{label}")

        first_repo = native_repository("first", first_inventory)
        second_repo = native_repository("second", second_inventory)
        installed = session.profile / "extensions" / REPO / "scenario"
        with serve(first_repo) as (server, url):
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
            session.step(
                "update",
                [
                    "--online-mode",
                    "--background",
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(ROOT / "tests/blender/repository_update.py"),
                    "--",
                    "--url",
                    url,
                    "--report",
                    str(evidence),
                ],
            )
            report["update"] = json.loads(evidence.read_text())
            if report["update"] != {"before": "1.0.0", "after": "2.0.0", "enabled": True}:
                raise ValueError("Missing native update and enabled-state evidence")
            verify_installed(second, installed)
            if not {"/index.json", "/scenario-1.0.0.zip", "/scenario-2.0.0.zip"}.issubset(
                server.requests
            ):
                raise ValueError("Native updater did not fetch both exact fixture archives")
            report["requests"] = server.requests
        report["server_stopped"] = True
        if profile_snapshot(normal_profile) != before:
            raise ValueError("Normal Blender profile changed during the run")
        report["normal_profile_unchanged"] = True
        report["archives"] = {first.name: sha256(first), second.name: sha256(second)}
        session.cleanup()
        report["profile_removed"] = not session.profile.exists() and not session.temporary.exists()
        report["status"] = "passed"
        print(
            "PASS: native install/update preserved enabled state and exact archive bytes",
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
