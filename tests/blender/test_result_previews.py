# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed session previews: dedicated lane, private cache and no scene mutation."""

import hashlib
import json
import os
import struct
import tempfile
import threading
import time
import unittest
import zlib
from pathlib import Path

import bpy
import httpx
from helpers import addon_name, submodule

CDN = "https://storage.example.invalid"
# SOI, a JFIF APP0 segment, a 32 by 24 baseline frame header and EOI.
JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    + b"\xff\xc0\x00\x11\x08"
    + struct.pack(">HH", 24, 32)
    + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xd9"
)
MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 64


def png(width, height):
    rows = b"".join(b"\x00" + b"\x40\x80\xc0\xff" * width for _ in range(height))

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


class SessionPreviewTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.job_session")
        self.api = submodule("core.api.sdk_adapter")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.previews = submodule("core.jobs.result_previews")
        directory = bpy.utils.extension_path_user(
            addon_name(), path="test-session-previews", create=True
        )
        self.temp = tempfile.TemporaryDirectory(dir=self.transfers._root(directory))
        self.addCleanup(self.temp.cleanup)
        self.root = (Path(directory) / Path(self.temp.name).name).resolve()
        self.results, self.cache = self.root / "results", self.root / "previews"
        self.results.mkdir()
        self.cache.mkdir()
        self.scope = self.storage.JobScope(
            "https://fixture.invalid/v1", "fixture-account", "fixture-project"
        )
        self.store = self.storage.JobStore(self.root / "jobs.sqlite3", self.scope)
        self.calls, self.downloads, self.gate = [], [], None
        self.thumbnail = f"{CDN}/still.jpg?signature=fixture"
        owner = self

        class OfflineDownloader(self.transfers.ResultDownloader):
            def download(self, url, *, root, name, max_bytes=None, **kwargs):
                owner.downloads.append(threading.current_thread())
                self._policy.destination(url)
                with (Path(root) / name).open("xb") as target:
                    target.write(JPEG)
                return owner.transfers.DownloadedResult(
                    name, len(JPEG), hashlib.sha256(JPEG).hexdigest()
                )

        self.downloader = OfflineDownloader(
            self.transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
            online_access=lambda: True,
        )
        self.session = self.new_session()
        self.addCleanup(lambda: self.session.shutdown())
        self.before = {
            name: len(getattr(bpy.data, name))
            for name in ("images", "objects", "scenes", "sounds", "movieclips", "meshes")
        }

    def respond(self, request):
        self.calls.append((request, threading.current_thread()))
        if self.gate is not None:
            self.gate()
        self.assertEqual((request.method, request.url.path), ("POST", "/v1/assets/get-bulk"))
        self.assertEqual(request.url.params["projectId"], self.scope.project_id)
        rows = [
            {
                "id": asset_id,
                "status": "success",
                "mimeType": "video/mp4",
                "url": f"{CDN}/result?signature=fixture",
                "thumbnail": {"assetId": "asset-still", "url": self.thumbnail},
            }
            for asset_id in json.loads(request.content)["assetIds"]
        ]
        return httpx.Response(200, json={"assets": rows})

    def new_session(self, **options):
        adapter = self.api.SDKAdapter(
            self.api.Credentials("fixture-key", "fixture-secret"),
            online=lambda: True,
            account_id=self.scope.account_id,
            project_id=self.scope.project_id,
            base_url=self.scope.service,
            transport=httpx.MockTransport(self.respond),
        )
        settings = {
            "workers": 1,
            "result_downloader": self.downloader,
            "result_root": self.results,
            "preview_root": self.cache,
        }
        settings.update(options)
        return self.module.JobSession(adapter, self.store, **settings)

    def ready(self, assets):
        origin = self.storage.JobOrigin("file", "scene", "revision")
        current = self.store.create(
            self.storage.JobIntent(
                "request", self.scope, origin, "model", "model", "a" * 64, "b" * 64, "1.0"
            )
        )
        state = self.storage.JobState
        for value in (state.SUBMITTING, state.REMOTE, state.SUCCEEDED):
            current = self.store.transition(
                "request",
                expected_revision=current.revision,
                state=value,
                remote_job_id="remote" if value == state.REMOTE else None,
            )
        manifest = tuple(
            self.storage.ResultAsset(identifier, f"{index:03d}-{identifier}.bin", kind, len(data))
            for index, (identifier, kind, data) in enumerate(assets)
        )
        current = self.store.set_results("request", manifest, expected_revision=current.revision)
        current = self.store.transition(
            "request", expected_revision=current.revision, state=state.DOWNLOADING
        )
        directory = self.session._coordinator._results._directory(current)
        for item, (_, _, data) in zip(manifest, assets, strict=True):
            (directory / item.name).write_bytes(data)
            receipt = self.transfers.DownloadedResult(
                item.name, len(data), hashlib.sha256(data).hexdigest()
            )
            current = self.store.record_download(
                "request", item.asset_id, receipt, expected_revision=current.revision
            )
        return self.store.transition(
            "request", expected_revision=current.revision, state=state.READY
        )

    def settle(self, predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            # The same maintenance entry point as GUI timers and headless loops.
            self.module.reap_retired()
            if predicate():
                return
            time.sleep(0.02)
        self.fail("Previews did not settle on the preview lane")

    def status(self, asset_id, rendition="still"):
        return self.session.result_previews.status("request", asset_id).get(rendition)

    def assertSceneUnchanged(self):
        after = {name: len(getattr(bpy.data, name)) for name in self.before}
        self.assertEqual(after, self.before)

    def test_server_still_and_image_decode_run_on_the_lane_without_scene_changes(self):
        record = self.ready(
            [("asset-video", "video/mp4", MP4), ("asset-image", "image/png", png(8, 4))]
        )
        statuses = self.session.result_previews.request("request")
        self.assertEqual([status.kind for status in statuses], ["video", "image"])
        ready, decode = self.previews.PreviewState.READY, self.previews.PreviewState.DECODE
        self.settle(
            lambda: (
                self.status("asset-video").state == ready
                and self.status("asset-image").state == decode
            )
        )
        still = self.status("asset-video").preview
        self.assertEqual(still.path.read_bytes(), JPEG)
        self.assertEqual((still.width, still.height), (32, 24))
        # Like saved results, cache paths use the root's canonical storage
        # spelling: Windows' extended \\?\ namespace, so deep entries stay usable.
        canonical = self.transfers._root(self.cache)
        if os.name == "nt":
            self.assertTrue(str(still.path).startswith("\\\\?\\"))
        self.assertTrue(still.path.is_relative_to(canonical))
        self.assertEqual([thread.name for _, thread in self.calls], ["ScenarioPreview"])
        self.assertEqual([thread.name for thread in self.downloads], ["ScenarioPreview"])
        (request,) = self.session.result_previews.decode_requests()
        self.assertTrue(request.source.is_relative_to(canonical / "work"))
        self.assertEqual(request.source.read_bytes(), png(8, 4))
        request.output.write_bytes(png(4, 2))
        self.session.result_previews.finish_decode(request)
        self.settle(lambda: self.status("asset-image").state == ready)
        self.assertEqual(self.status("asset-image").preview.width, 4)
        self.assertFalse(request.directory.exists())
        self.assertSceneUnchanged()
        self.assertEqual(self.store.get("request"), record)

    def test_retirement_closes_previews_and_shutdown_removes_private_copies(self):
        self.ready([("asset-image", "image/png", png(8, 4))])
        previews = self.session.result_previews
        previews.request("request")
        decode = self.previews.PreviewState.DECODE
        self.settle(lambda: self.status("asset-image").state == decode)
        (request,) = previews.decode_requests()
        self.session.deactivate()
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.result_previews  # noqa: B018 - the property enforces activity
        self.assertFalse(self.session.service_previews())
        self.session.shutdown()
        self.assertFalse(request.directory.exists())
        self.assertEqual(self.calls, [])
        self.assertSceneUnchanged()

    def test_retirement_never_joins_an_inflight_preview_read_on_the_main_thread(self):
        self.ready([("asset-video", "video/mp4", MP4)])
        entered, release = threading.Event(), threading.Event()

        def gate():
            # Like an SDK read in flight, this does not watch the lane's cancel event.
            entered.set()
            release.wait(10)

        self.gate = gate
        self.addCleanup(release.set)
        self.session.result_previews.request("request")
        self.module.reap_retired()
        self.assertTrue(entered.wait(5))
        self.session.deactivate()
        started = time.monotonic()
        self.module.reap_retired()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertIn(self.session, self.module._session_snapshot())
        self.assertFalse(self.session._workers.stopped)
        release.set()
        self.settle(lambda: self.session not in self.module._session_snapshot())
        self.assertTrue(self.session._workers.stopped)
        self.assertEqual(self.downloads, [])
        self.assertFalse(any((self.cache / "work").glob("preview-*")))
        self.assertSceneUnchanged()

    def test_unconfigured_sessions_and_worker_threads_are_rejected(self):
        self.session.shutdown()
        self.session = self.new_session(preview_root=None)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.result_previews  # noqa: B018 - the property enforces configuration
        self.assertFalse(self.session.service_previews())
        errors = []

        def worker():
            try:
                self.session.service_previews()
            except RuntimeError as error:
                errors.append(error)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        self.assertEqual(len(errors), 1)
