# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed local MCP inspection of saved result previews and audio envelopes.

The tool reads the same session scheduler as the native preview tiles and the
Waveform control. Server stills come from a synthetic SDK transport and an
offline storage stub, audio envelopes from the real offline Blender decoder;
nothing contacts Scenario and no player is launched.
"""

import hashlib
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import online_access, submodule, temp_credentials
from test_result_media import tone
from test_result_preview_tiles import CDN, MP4, png

CANCELED = "Preview decoding was canceled; use Retry"


class McpResultPreviewTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.runtime = submodule("blender.runtime")
        self.tiles = submodule("blender.result_previews")
        self.media = submodule("blender.result_media")
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
        self.requests, self.sessions, self.thumbnails, self.types = [], [], {}, {}
        catalog_type, session_type = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.requests.append(request)
            if (request.method, request.url.path) != ("POST", "/v1/assets/get-bulk"):
                raise AssertionError("Previews read only asset metadata from Scenario")
            rows = []
            for asset_id in json.loads(request.content)["assetIds"]:
                row = {"id": asset_id, "status": "success", "mimeType": self.types[asset_id]}
                if asset_id in self.thumbnails:
                    row["thumbnail"] = {
                        "assetId": f"{asset_id}-thumb",
                        "url": self.thumbnails[asset_id],
                    }
                rows.append(row)
            return httpx.Response(200, json={"assets": rows})

        def adapter(credentials, **options):
            return api.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **options)

        def session(*args, **options):
            value = session_type(*args, **options)
            self.sessions.append(value)
            return value

        owner = self
        self.files = {}

        class OfflineDownloader(self.transfers.ResultDownloader):
            """The real host policy and verification, with bytes served from memory."""

            def download(self, url, *, root, name, max_bytes=None, **kwargs):
                self._policy.destination(url)
                data = owner.files[url]
                with (Path(root) / name).open("xb") as target:
                    target.write(data)
                return owner.transfers.DownloadedResult(
                    name, len(data), hashlib.sha256(data).hexdigest()
                )

        self.enterContext(
            patch.object(
                self.runtime,
                "SDKCatalog",
                side_effect=lambda *a, **k: catalog_type(*a, adapter_factory=adapter, **k),
            )
        )
        self.enterContext(patch.object(self.runtime, "JobSession", side_effect=session))
        self.enterContext(patch.object(self.runtime, "ResultDownloader", OfflineDownloader))
        self.tiles.controller.retire()
        self.media.controller.retire()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.tiles.controller.retire()
        self.media.controller.retire()
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    def saved(self, assets, request_id="request", *, download=True):
        """A saved job whose receipts match private local bytes; READY when downloaded."""
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
            m.ResultAsset(asset_id, name, media_type, len(data), texture_role=role)
            for asset_id, name, media_type, data, *rest in assets
            for role in (rest[0] if rest else None,)
        )
        self.types.update({item.asset_id: item.media_type for item in manifest})
        current = store.set_results(request_id, manifest, expected_revision=current.revision)
        if download:
            current = store.transition(
                request_id, expected_revision=current.revision, state=m.JobState.DOWNLOADING
            )
            directory = session._coordinator._results._directory(current)
            for item, (_, _, _, data, *_) in zip(manifest, assets, strict=True):
                (directory / item.name).write_bytes(data)
                receipt = self.transfers.DownloadedResult(
                    item.name, len(data), hashlib.sha256(data).hexdigest()
                )
                current = store.record_download(
                    request_id, item.asset_id, receipt, expected_revision=current.revision
                )
            store.transition(request_id, expected_revision=current.revision, state=m.JobState.READY)
        self.runtime.inspect_model_jobs()
        return store.get(request_id)

    def args(self, record, **values):
        return {
            "context_id": self.runtime.state.job_context_id,
            "request_id": record.intent.request_id,
            "expected_revision": record.revision,
            **values,
        }

    def pump(self):
        # The same main-thread entry points as the GUI timers and headless loops.
        self.module.reap_retired()
        self.tiles.controller.poll()

    def inspect_until(self, args, predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump()
            result = self.mcp.inspect_result_previews(args)
            if predicate(result):
                return result
            time.sleep(0.01)
        self.fail(f"Previews did not settle: {result}")

    def wait(self, deferred, timeout=30):
        """Run a deferred wait on a worker thread while this main thread pumps."""
        self.assertIsInstance(deferred, self.protocol.DeferredTool)
        waiter = threading.Thread(target=deferred.run, name="McpWait")
        waiter.start()
        deadline = time.monotonic() + timeout
        while waiter.is_alive():
            self.assertLess(time.monotonic(), deadline, "The deferred wait did not return")
            self.pump()
            time.sleep(0.01)
        return deferred.finish(None)

    def blocked_decode(self):
        """Hold the offline decoder until it is canceled, like a long decode."""
        decoder = submodule("core.jobs.audio_decode")
        canceled = submodule("core.jobs.local_render").RenderCancelled
        started, stopped = threading.Event(), []

        def run(command, *, cancel, **options):
            started.set()
            if not cancel.wait(10):
                raise AssertionError("The waveform decoder was not canceled")
            stopped.append(threading.current_thread().name)
            raise canceled("Local capture cancelled")

        patcher = patch.object(decoder, "_run", side_effect=run)
        patcher.start()
        self.addCleanup(patcher.stop)
        return started, stopped, patcher

    def idle(self):
        return self.runtime.state.job_session._workers.previews_idle

    # -- inspection -----------------------------------------------------------

    def test_default_inspection_reports_every_previewable_result_without_paths_or_urls(self):
        url = f"{CDN}/clip-thumb.png?signature=fixture"
        self.thumbnails["clip"], self.files[url] = url, png(320, 180)
        with online_access(True):
            record = self.saved(
                [
                    ("clip", "clip.mp4", "video/mp4", MP4),
                    ("sound", "sound.wav", "audio/wav", tone()),
                    ("image", "image.png", "image/png", png(64, 32)),
                    ("normal", "normal.png", "image/png", png(8, 8), "normal"),
                    ("second", "second.png", "image/png", png(8, 8)),
                    ("notes", "notes.txt", "text/plain", b"notes"),
                ]
            )
            scheduler = self.runtime.state.job_session.result_previews
            scheduler._delays, scheduler._window = (0.05,), 0.2
            first = self.mcp.inspect_result_previews(self.args(record))
            self.assertTrue(first["in_progress"])
            # Every previewable result, ranked as the tiles are; MCP has no pager.
            self.assertNotIn("more_results", first)
            self.assertEqual(
                [(item["asset_id"], item["number"], item["caption"]) for item in first["results"]],
                [
                    ("clip", 1, "Video (1)"),
                    ("sound", 2, "Audio (2)"),
                    ("image", 3, "Image (3)"),
                    ("second", 5, "Image (5)"),
                    ("normal", 4, "Normal (4)"),
                ],
            )
            result = self.inspect_until(self.args(record), lambda value: not value["in_progress"])
        clip, sound, image, second, normal = result["results"]
        self.assertEqual(
            (clip["media_type"], clip["kind"], clip["renditions"]),
            (
                "video/mp4",
                "video",
                {
                    "still": {
                        "state": "ready",
                        "source": "scenario",
                        "media_type": "image/png",
                        "width": 320,
                        "height": 180,
                        "size": len(png(320, 180)),
                    }
                },
            ),
        )
        missing = sound["renditions"]["still"]
        self.assertEqual((missing["state"], missing["source"]), ("missing", "scenario"))
        self.assertIn("no preview", missing["reason"])
        self.assertNotIn("envelope", sound["renditions"])  # Only Waveform or envelope=true.
        local = image["renditions"]["still"]
        self.assertEqual(
            {key: local[key] for key in ("state", "source", "media_type", "width", "height")},
            {
                "state": "ready",
                "source": "local",
                "media_type": "image/png",
                "width": 64,
                "height": 32,
            },
        )
        self.assertEqual(second["renditions"]["still"]["state"], "ready")
        self.assertEqual(normal["renditions"]["still"]["state"], "ready")
        # The native tiles draw the same ranked results from the same scheduler,
        # four at a time: the normal map is on their second page.
        tiles = self.tiles.controller.tiles["request"]
        self.assertEqual(
            [(tile.asset_id, tile.caption) for tile in tiles],
            [(item["asset_id"], item["caption"]) for item in result["results"][:4]],
        )
        self.assertEqual(self.tiles.controller.pages["request"].label, "1-4 of 5")
        text = json.dumps(result)
        for private in (str(self.root), "http", "signature", "result-previews", "sound.wav"):
            self.assertNotIn(private, text)
        # One result by asset_id, here one on the tiles' second page.
        (normal,) = self.mcp.inspect_result_previews(self.args(record, asset_id="normal"))[
            "results"
        ]
        self.assertEqual((normal["caption"], normal["kind"]), ("Normal (4)", "image"))
        notes = self.inspect_until(
            self.args(record, asset_id="notes"), lambda value: not value["in_progress"]
        )
        # No preview kind: never a lane request, and no source is claimed.
        self.assertEqual(
            notes["results"][0]["renditions"],
            {
                "still": {
                    "state": "unsupported",
                    "reason": "No preview is available for this format",
                }
            },
        )
        # The served tool returns the same JSON through the MCP protocol.
        registry = submodule("blender.mcp_service").build_registry()
        response = self.protocol.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "inspect_result_previews", "arguments": self.args(record)},
            },
            registry,
            {"name": "test", "version": "0"},
        )
        self.assertNotIn("isError", response["result"])
        served = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(served, self.mcp.inspect_result_previews(self.args(record)))
        self.assertEqual(self.runtime.state.job_store.get("request"), record)
        self.assertEqual({request.url.path for request in self.requests}, {"/v1/assets/get-bulk"})

    def test_a_roughness_map_is_captioned_by_its_role_like_its_tile(self):
        # A roughness map from a 3D texture set once read "Image (1)" here too.
        with online_access(False):
            record = self.saved(
                [("roughness", "roughness.png", "image/png", png(8, 8), "roughness")]
            )
            result = self.inspect_until(self.args(record), lambda value: not value["in_progress"])
        (item,) = result["results"]
        self.assertEqual((item["caption"], item["kind"]), ("Roughness (1)", "image"))
        (tile,) = self.tiles.controller.tiles["request"]
        self.assertEqual(tile.caption, item["caption"])

    def test_an_envelope_wait_runs_off_the_main_thread_and_returns_bounded_levels(self):
        with online_access(False):
            record = self.saved([("sound", "sound.wav", "audio/wav", tone())])
            deferred = self.mcp.inspect_result_previews(
                self.args(record, asset_id="sound", envelope=True, bins=16, wait=30)
            )
            result = self.wait(deferred)
            self.assertFalse(result["in_progress"])
            (sound,) = result["results"]
            envelope = sound["renditions"]["envelope"]
            levels = {key: envelope.pop(key) for key in ("rms", "peaks", "overall_rms")}
            peak = envelope.pop("overall_peak")
            self.assertEqual(
                envelope,
                {
                    "state": "ready",
                    "seconds": 0.25,
                    "sample_rate": 8000,
                    "channels": 1,
                    "silent": False,
                    "bins": 16,
                },
            )
            self.assertAlmostEqual(peak, 0.5, delta=0.01)
            self.assertEqual((len(levels["rms"]), len(levels["peaks"])), (16, 16))
            self.assertEqual(max(levels["peaks"]), peak)
            self.assertTrue(
                all(
                    0 <= rms <= top for rms, top in zip(levels["rms"], levels["peaks"], strict=True)
                )
            )
            self.assertEqual(sound["renditions"]["still"]["state"], "offline")
            # The Waveform control reads the envelope this request decoded.
            self.media.controller.select_waveform(
                self.runtime.state.job_context_id, "request", record.revision, "sound"
            )
            self.assertEqual(self.media.controller.selection.status, "READY")
            # Without a wait, a cached envelope is answered at once.
            again = self.mcp.inspect_result_previews(
                self.args(record, asset_id="sound", envelope=True, wait=30)
            )
            self.assertIsInstance(again, dict)
            self.assertEqual(again["results"][0]["renditions"]["envelope"]["bins"], 25)
        self.assertEqual(self.requests, [])
        self.assertEqual(self.runtime.state.job_store.get("request"), record)

    def test_an_envelope_wait_does_not_wait_for_a_still_that_keeps_polling(self):
        with online_access(True):
            # Scenario has no still for this audio yet, so it polls for minutes.
            record = self.saved([("sound", "sound.wav", "audio/wav", tone())])
            began = time.monotonic()
            deferred = self.mcp.inspect_result_previews(
                self.args(record, asset_id="sound", envelope=True, wait=60)
            )
            result = self.wait(deferred, timeout=30)
            self.assertLess(time.monotonic() - began, 30)
        (sound,) = result["results"]
        self.assertEqual(sound["renditions"]["envelope"]["state"], "ready")
        self.assertEqual(sound["renditions"]["still"]["state"], "pending")
        self.assertTrue(result["in_progress"])  # The still is still in progress.
        self.assertEqual({request.url.path for request in self.requests}, {"/v1/assets/get-bulk"})

    def test_cancel_and_retry_mirror_the_native_controls(self):
        with online_access(False):
            record = self.saved([("sound", "sound.wav", "audio/wav", tone())])
            started, stopped, patcher = self.blocked_decode()
            args = self.args(record, asset_id="sound", envelope=True)
            loading = self.mcp.inspect_result_previews(args)
            self.assertTrue(loading["in_progress"])
            deadline = time.monotonic() + 30
            while not started.is_set():
                self.assertLess(time.monotonic(), deadline)
                self.pump()
                time.sleep(0.01)
            canceled = self.mcp.inspect_result_previews(dict(args, action="cancel"))
            envelope = canceled["results"][0]["renditions"]["envelope"]
            self.assertEqual(envelope, {"state": "failed", "reason": CANCELED})
            deadline = time.monotonic() + 30
            while stopped != ["ScenarioPreview"] or not self.idle():
                self.assertLess(time.monotonic(), deadline)
                self.pump()
                time.sleep(0.01)
            patcher.stop()
            controller = self.tiles.controller
            # A retry also lets the tile build an icon that failed before, as Retry does.
            with patch.object(
                controller, "forget_failures", wraps=controller.forget_failures
            ) as forget:
                deferred = self.mcp.inspect_result_previews(dict(args, action="retry", wait=30))
            forget.assert_called_once_with("request", "sound")
            retried = self.wait(deferred)
            self.assertEqual(retried["results"][0]["renditions"]["envelope"]["state"], "ready")
        self.assertEqual(self.requests, [])

    def test_a_context_change_ends_a_wait_and_its_late_result_is_refused(self):
        with online_access(False):
            record = self.saved([("sound", "sound.wav", "audio/wav", tone())])
            started, _, _ = self.blocked_decode()
            deferred = self.mcp.inspect_result_previews(
                self.args(record, asset_id="sound", envelope=True, wait=60)
            )
            waiter = threading.Thread(target=deferred.run)
            waiter.start()
            deadline = time.monotonic() + 30
            while not started.is_set():
                self.assertLess(time.monotonic(), deadline)
                self.pump()
                time.sleep(0.01)
            began = time.monotonic()
            self.runtime.state.reset()  # Credentials, project or file changed.
            waiter.join(5)
            self.assertFalse(waiter.is_alive())
            self.assertLess(time.monotonic() - began, 5)
            with self.assertRaisesRegex(Exception, "changed while waiting"):
                deferred.finish(None)

    def test_a_wait_a_stopped_server_never_delivers_frees_its_watch(self):
        # Adapted from a review finding: only the main-thread delivery dropped the
        # watch, and a stopped server never queues that delivery.
        with online_access(False):
            record = self.saved([("sound", "sound.wav", "audio/wav", tone())])
            started, _, _ = self.blocked_decode()
            server = SimpleNamespace(running=True)
            self.runtime.state.mcp = server
            deferred = self.mcp.inspect_result_previews(
                self.args(record, asset_id="sound", envelope=True, wait=60)
            )
            scheduler = self.runtime.state.job_session.result_previews
            self.assertEqual(len(scheduler._watches), 1)
            waiter = threading.Thread(target=deferred.run, name="McpWait")
            waiter.start()
            deadline = time.monotonic() + 30
            while not started.is_set():
                self.assertLess(time.monotonic(), deadline)
                self.pump()
                time.sleep(0.01)
            server.running = False
            waiter.join(5)
            self.assertFalse(waiter.is_alive())
            self.pump()
            # The decode still runs, yet the abandoned wait holds no watch.
            self.assertFalse(scheduler.quiet("request", "sound", ("envelope",)))
            self.assertEqual(scheduler._watches, [])

    def test_a_wait_refuses_a_saved_job_that_changed_while_it_waited(self):
        error = submodule("core.api.errors").ScenarioError
        with online_access(False):
            record = self.saved([("sound", "sound.wav", "audio/wav", tone())])
            deferred = self.mcp.inspect_result_previews(
                self.args(record, asset_id="sound", envelope=True, wait=0.2)
            )
            deferred.run()  # Nothing pumps here, so the envelope is still queued.
            # Another action changes the saved job while the agent waits.
            changed = self.runtime.state.job_store.transition(
                "request",
                expected_revision=record.revision,
                state=self.storemod.JobState.APPLYING,
            )
            self.assertGreater(changed.revision, record.revision)
            with self.assertRaisesRegex(error, "saved job changed while waiting"):
                deferred.finish(None)
            self.assertEqual(self.runtime.state.job_session.result_previews._watches, [])

    def test_stale_invalid_or_unsupported_requests_are_refused(self):
        error = submodule("core.api.errors").ScenarioError
        with online_access(False):
            record = self.saved(
                [
                    ("clip", "clip.mp4", "video/mp4", MP4),
                    ("sound", "sound.wav", "audio/wav", tone()),
                ]
            )
            pending = self.saved(
                [("later", "later.wav", "audio/wav", tone())], "pending", download=False
            )
            refused = {
                "context": (self.args(record, context_id="another"), error, "context changed"),
                "revision": (
                    self.args(record, expected_revision=record.revision + 1),
                    error,
                    "changed",
                ),
                "not downloaded": (self.args(pending), error, "Download the saved result"),
                "unknown asset": (self.args(record, asset_id="absent"), error, "from this job"),
                "video envelope": (
                    self.args(record, asset_id="clip", envelope=True),
                    error,
                    "audio",
                ),
                "envelope for all": (self.args(record, envelope=True), ValueError, "asset_id"),
                "retry for all": (self.args(record, action="retry"), ValueError, "asset_id"),
                "player": (self.args(record, action="play"), ValueError, "action"),
                "bins": (self.args(record, bins=4), ValueError, "bins"),
                "boolean bins": (self.args(record, bins=True), ValueError, "bins"),
                "wait": (self.args(record, wait=61), ValueError, "wait"),
                "boolean wait": (self.args(record, wait=True), ValueError, "wait"),
                "revision type": (self.args(record, expected_revision="1"), ValueError, "revision"),
                "never requested": (
                    self.args(record, asset_id="sound", action="cancel"),
                    error,
                    "No preview",
                ),
            }
            for name, (args, kind, message) in refused.items():
                with self.subTest(name=name), self.assertRaisesRegex(kind, message):
                    self.mcp.inspect_result_previews(args)
        self.assertEqual(self.requests, [])
        self.assertEqual(self.runtime.state.job_store.get("request"), record)

    def test_registered_tool_is_read_only_and_launches_no_player(self):
        registry = submodule("blender.mcp_service").build_registry()
        spec = registry.get("inspect_result_previews")
        self.assertEqual(spec.annotations, {"readOnlyHint": True})
        self.assertFalse(spec.offthread)
        self.assertEqual(
            set(spec.input_schema["properties"]),
            {
                "context_id",
                "request_id",
                "expected_revision",
                "asset_id",
                "envelope",
                "action",
                "bins",
                "wait",
            },
        )
        self.assertEqual(
            spec.input_schema["properties"]["action"]["enum"], list(self.mcp.PREVIEW_ACTIONS)
        )
        names = registry.names()
        self.assertFalse([name for name in names if "play" in name])


if __name__ == "__main__":
    unittest.main()
