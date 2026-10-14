# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed local MCP job_status lists the verified local files of saved results.

Results are saved through the real store with offline bytes, never imported:
a video, an image, audio, a 3D model and text. The served tool reports their
files once the preview lane has rehashed them, again after the session is
rebuilt as a restart would, and never a missing or changed file. Nothing
contacts Scenario.
"""

import hashlib
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import submodule, temp_credentials
from test_result_preview_tiles import MP4, png

WAV = b"RIFF" + b"\x00" * 40
GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 24

RESULTS = (
    ("clip", "000-clip.mp4", "video/mp4", MP4),
    ("still", "001-still.png", "image/png", png(8, 8)),
    ("sound", "002-sound.wav", "audio/wav", WAV),
    ("mesh", "003-mesh.glb", "model/gltf-binary", GLB),
    ("notes", "004-notes.txt", "text/plain", b"plain words"),
)


class McpJobFilesTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.runtime = submodule("blender.runtime")
        self.mcp = submodule("mcp.tools_scenario")
        self.protocol = submodule("mcp.protocol")
        self.storemod = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.module = submodule("blender.job_session")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        source = self.prefs.credential_source
        self.addCleanup(setattr, self.prefs, "credential_source", source)
        self.prefs.credential_source = "PREFERENCES"
        root = self.enterContext(tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")))
        self.root = Path(root).resolve()
        self.enterContext(
            patch.object(
                self.runtime,
                "paths",
                return_value=SimpleNamespace(state_dir=self.root, cache_dir=self.root / "cache"),
            )
        )
        api = submodule("core.api.sdk_adapter")
        self.requests, self.sessions = [], []
        catalog_type, session_type = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.requests.append(request)
            raise AssertionError("Checking saved files never contacts Scenario")

        def adapter(credentials, **options):
            return api.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **options)

        def session(*args, **options):
            value = session_type(*args, **options)
            self.sessions.append(value)
            return value

        self.enterContext(
            patch.object(
                self.runtime,
                "SDKCatalog",
                side_effect=lambda *a, **k: catalog_type(*a, adapter_factory=adapter, **k),
            )
        )
        self.enterContext(patch.object(self.runtime, "JobSession", side_effect=session))
        self.addCleanup(self.cleanup)
        self.registry = submodule("blender.mcp_service").build_registry()

    def cleanup(self):
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    def saved(self, request_id="request"):
        """A READY job whose receipts match private local bytes, never imported."""
        m = self.storemod
        store = self.runtime.ensure_job_store()
        session = self.runtime.ensure_job_session()
        current = store.create(
            m.JobIntent(
                request_id,
                store.scope,
                m.JobOrigin("file", "scene", "revision"),
                "model",
                "model",
                "a" * 64,
                "b" * 64,
                "0.10000000000000001",
            )
        )
        for state in (m.JobState.SUBMITTING, m.JobState.REMOTE, m.JobState.SUCCEEDED):
            current = store.transition(
                request_id,
                expected_revision=current.revision,
                state=state,
                remote_job_id=f"remote-{request_id}" if state == m.JobState.REMOTE else None,
            )
        manifest = tuple(
            m.ResultAsset(asset_id, name, media_type, len(data))
            for asset_id, name, media_type, data in RESULTS
        )
        current = store.set_results(request_id, manifest, expected_revision=current.revision)
        current = store.transition(
            request_id, expected_revision=current.revision, state=m.JobState.DOWNLOADING
        )
        directory = session._coordinator._results._directory(current)
        for item, (_, _, _, data) in zip(manifest, RESULTS, strict=True):
            (directory / item.name).write_bytes(data)
            receipt = self.transfers.DownloadedResult(
                item.name, len(data), hashlib.sha256(data).hexdigest()
            )
            current = store.record_download(
                request_id, item.asset_id, receipt, expected_revision=current.revision
            )
        store.transition(request_id, expected_revision=current.revision, state=m.JobState.READY)
        return directory

    def served(self, name, arguments):
        """Call the tool through the installed registry and MCP protocol."""
        response = self.protocol.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            self.registry,
            {"name": "test", "version": "0"},
        )
        self.assertNotIn("isError", response["result"], response)
        return json.loads(response["result"]["content"][0]["text"])

    def status_until_checked(self, reference="request", timeout=30):
        """Read job_status like an agent would until no file check is pending."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.module.reap_retired()
            status = self.served("job_status", {"job_id": reference})
            if not status["file_check_pending"]:
                return status
            time.sleep(0.01)
        raise self.failureException(f"File checks did not settle: {status}")

    def wait(self, deferred, timeout=30):
        """Run a deferred wait on a worker thread while this main thread pumps."""
        self.assertIsInstance(deferred, self.protocol.DeferredTool)
        waiter = threading.Thread(target=deferred.run, name="McpWait")
        waiter.start()
        deadline = time.monotonic() + timeout
        while waiter.is_alive():
            self.assertLess(time.monotonic(), deadline, "The deferred wait did not return")
            self.module.reap_retired()
            self.runtime.state.model_jobs.poll()
            time.sleep(0.01)
        return deferred.finish(None)

    def restart(self):
        """Retire the session and its memory; the saved store and files remain."""
        self.runtime.state.reset()
        self.module.reap_retired()
        self.assertIsNone(self.runtime.state.model_jobs)

    def assert_listed(self, status, directory):
        expected = [str(directory / name) for _, name, _, _ in RESULTS]
        self.assertEqual(status["files"], expected)
        self.assertEqual(
            [(row["asset_id"], row["file"], row["file_state"]) for row in status["results"]],
            [
                (asset_id, path, "verified")
                for (asset_id, *_), path in zip(RESULTS, expected, strict=True)
            ],
        )
        for path, (*_, data) in zip(status["files"], RESULTS, strict=True):
            self.assertEqual(Path(path).read_bytes(), data)

    def test_ready_results_of_every_kind_list_their_verified_files(self):
        directory = self.saved()
        first = self.served("job_status", {"job_id": "request"})
        # Nothing is listed before the preview lane has rehashed it.
        self.assertTrue(first["file_check_pending"])
        self.assertEqual(first["files"], [])
        self.assertEqual({row["file_state"] for row in first["results"]}, {"checking"})
        status = self.status_until_checked()
        self.assertEqual((status["status"], status["kind"]), ("ready", "model"))
        self.assertEqual(status["images"], [])
        self.assert_listed(status, directory)
        # The remote job ID finds the same saved job and files.
        self.assertEqual(self.served("job_status", {"job_id": "remote-request"}), status)
        self.assertNotIn("http", json.dumps(status))
        self.assertEqual(self.requests, [])

    def test_a_restarted_session_lists_the_files_from_the_saved_store(self):
        directory = self.saved()
        self.assert_listed(self.status_until_checked(), directory)
        before = self.runtime.state.job_store.get("request")
        self.restart()
        # Fresh store connection, session and job memory, as after a restart.
        status = self.served("job_status", {"job_id": "request"})
        self.assertIsNotNone(self.runtime.state.model_jobs)
        self.assertNotIn("request", self.runtime.state.model_jobs.views)
        self.assertTrue(status["file_check_pending"])
        self.assert_listed(self.status_until_checked(), directory)
        self.assertEqual(self.runtime.state.job_store.get("request"), before)
        self.assertEqual(self.requests, [])

    def test_wait_for_job_returns_once_the_restarted_job_files_are_checked(self):
        directory = self.saved()
        self.restart()
        status = self.wait(self.mcp.wait_for_job({"job_id": "request", "timeout": 30}))
        self.assertFalse(status["file_check_pending"])
        self.assert_listed(status, directory)

    def test_missing_or_changed_files_are_reported_but_never_listed(self):
        directory = self.saved()
        self.assert_listed(self.status_until_checked(), directory)
        (directory / "000-clip.mp4").unlink()
        changed = directory / "003-mesh.glb"
        staged = changed.with_name("staged.glb")
        staged.write_bytes(GLB[:-1] + b"\x01")
        os.replace(staged, changed)
        partial = directory / "002-sound.wav"
        partial.write_bytes(WAV[:8])
        status = self.status_until_checked()
        self.assertEqual(
            [(row["asset_id"], row["file_state"]) for row in status["results"]],
            [
                ("clip", "missing"),
                ("still", "verified"),
                ("sound", "changed"),
                ("mesh", "changed"),
                ("notes", "verified"),
            ],
        )
        self.assertEqual(
            status["files"], [str(directory / "001-still.png"), str(directory / "004-notes.txt")]
        )
        self.assertTrue(all(row["downloaded"] for row in status["results"]))
        self.assertEqual(
            [row["file"] for row in status["results"] if row["file_state"] != "verified"],
            [None, None, None],
        )
        # After a restart the same files are still refused.
        self.restart()
        again = self.status_until_checked()
        self.assertEqual(again["files"], status["files"])
        self.assertEqual(
            [row["file_state"] for row in again["results"]],
            [row["file_state"] for row in status["results"]],
        )


if __name__ == "__main__":
    unittest.main()
