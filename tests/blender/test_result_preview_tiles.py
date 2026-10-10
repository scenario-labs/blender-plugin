# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed automatic result previews in Jobs, Generations and Studio rows.

Saved images decode on Blender's main thread from private verified copies,
inside a temporary data block. Server stills come from a synthetic SDK
transport and an offline storage stub; nothing contacts Scenario. Drawing is
checked through recording layouts, not physical input.
"""

import builtins
import hashlib
import io
import json
import os
import struct
import tempfile
import threading
import time
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

import bpy
from helpers import draw_job_panels, online_access, submodule, temp_credentials

MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 64
CDN = "https://cdn.cloud.scenario.com"


def png(width, height, pixel=b"\x40\x80\xc0\xff"):
    rows = b"".join(b"\x00" + pixel * width for _ in range(height))

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


def corrupt_png(width, height):
    """A valid signature and header whose image data cannot be decoded."""
    data = png(width, height)
    start = data.index(b"IDAT") + 4
    return data[:start] + b"\x00" * 32 + data[start + 32 :]


class Layout:
    """Records draw calls, including nested rows, columns and boxes, in order."""

    def __init__(self, calls=None):
        self.calls = [] if calls is None else calls

    def box(self):
        self.calls.append(("box",))
        return self

    def row(self, align=False):
        self.calls.append(("row",))
        return self

    def column(self, align=False):
        self.calls.append(("column",))
        return self

    def label(self, *, text, icon="NONE"):
        self.calls.append(("label", text, icon))

    def operator(self, idname, *, text="", icon="NONE", emboss=True):
        properties = {}
        self.calls.append(("operator", idname, text, icon, properties))
        return _Properties(properties)

    def template_icon(self, *, icon_value, scale):
        self.calls.append(("icon", icon_value, scale))


class _Properties:
    def __init__(self, properties):
        object.__setattr__(self, "_values", properties)

    def __setattr__(self, name, value):
        self._values[name] = value


class ResultPreviewTileTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.runtime = submodule("blender.runtime")
        self.tiles = submodule("blender.result_previews")
        self.storemod = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.previews = submodule("core.jobs.result_previews")
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
        self.requests, self.sessions, self.thumbnails = [], [], {}
        catalog_type, session_type = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.requests.append(request)
            if (request.method, request.url.path) != ("POST", "/v1/assets/get-bulk"):
                raise AssertionError("Previews read only asset metadata from Scenario")
            rows = []
            for asset_id in json.loads(request.content)["assetIds"]:
                row = {"id": asset_id, "status": "success", "mimeType": "video/mp4"}
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
        self.files, self.downloads, self.incomplete = {}, [], 0

        class OfflineDownloader(self.transfers.ResultDownloader):
            """The real host policy and verification, with bytes served from memory."""

            def download(self, url, *, root, name, max_bytes=None, **kwargs):
                self._policy.destination(url)
                owner.downloads.append((url, threading.current_thread().name))
                if owner.incomplete:
                    owner.incomplete -= 1
                    # A signed thumbnail URL that redirects to another host on first access.
                    raise owner.transfers.TransferError("Storage redirect destination rejected")
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
        # The OS thumbnail cache must never receive a private result.
        self.enterContext(
            patch.object(
                bpy.utils.previews.ImagePreviewCollection,
                "load",
                side_effect=AssertionError("Previews must not use the OS thumbnail cache"),
            )
        )
        self.tiles.controller.retire()
        self.addCleanup(self.cleanup)
        self.counts = self.data_counts()

    def cleanup(self):
        self.tiles.controller.retire()
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    @staticmethod
    def data_counts():
        return {
            name: len(getattr(bpy.data, name))
            for name in ("images", "scenes", "objects", "materials", "textures", "worlds")
        }

    def saved(self, assets, request_id="request"):
        """A READY job whose receipts match private local bytes; the projected view."""
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
        current = store.set_results(request_id, manifest, expected_revision=current.revision)
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
        self.results = directory
        owner = self.runtime.inspect_model_jobs()
        return owner.views[request_id]

    def fast_polling(self, *, window=30.0):
        """Shorten the scheduler's waits; its lane and window logic stay real."""
        scheduler = self.runtime.state.job_session.result_previews
        scheduler._delays, scheduler._window = (0.05,), window

    def settle(self, predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # The same main-thread entry points as the GUI timers.
            self.module.reap_retired()
            self.tiles.controller.poll()
            if predicate():
                return
            time.sleep(0.01)
        self.fail(f"Previews did not settle: {self.tiles.controller.tiles}")

    def tile(self, request_id="request", index=0):
        tiles = self.tiles.controller.tiles.get(request_id, ())
        return tiles[index] if len(tiles) > index else None

    def status(self, request_id="request", index=0):
        tile = self.tile(request_id, index)
        return None if tile is None else tile.status

    def icon(self, request_id="request", index=0):
        tile = self.tile(request_id, index)
        collection = self.tiles.controller._previews
        (key,) = [
            key
            for key, value in self.tiles.controller._icons.items()
            if key.startswith(f"{request_id}/{tile.asset_id}/") and value == tile.icon_id
        ]
        return collection[key]

    def draw(self, view):
        """Draw one row's tiles with file and store access refused."""
        layout = Layout()
        store = self.runtime.state.job_store
        refused = AssertionError("File or store access while drawing")
        with (
            patch.object(builtins, "open", side_effect=refused),
            patch.object(io, "open", side_effect=refused),
            patch.object(os, "open", side_effect=refused),
            patch.object(os, "stat", side_effect=refused),
            patch.object(store, "get", side_effect=refused),
            patch.object(store, "records", side_effect=refused),
        ):
            self.tiles.draw(layout, view)
        return layout.calls

    # -- saved images ---------------------------------------------------------

    def test_saved_image_decodes_outside_the_open_file_into_a_cached_icon(self):
        # Image copies and icons use the shared temporary decode, not a copy of it.
        helper = submodule("blender.preview_decode")
        self.assertIs(self.tiles.decode, helper.decode)
        self.assertIs(self.tiles.PreviewDecodeError, helper.PreviewDecodeError)
        with online_access(False):
            view = self.saved([("image", "result.png", "image/png", png(640, 320))])
            dirty = bpy.data.is_dirty
            session = self.runtime.state.job_session
            (origin,) = session.capture_many(bpy.context.scene, (None,))
            self.settle(lambda: self.status() == "ready")
            # No data reached the open file's dependency graph: a captured scene
            # origin, which any scene update invalidates, is still current.
            bpy.context.view_layer.update()
            self.assertTrue(session._origins.current(origin))
        tile = self.tile()
        self.assertEqual((tile.caption, tile.number, tile.kind), ("Image (1)", 1, "image"))
        preview = self.icon()
        self.assertEqual(tuple(preview.image_size), (256, 128))
        first = tuple(round(value, 2) for value in preview.image_pixels_float[:4])
        self.assertEqual(first, (0.25, 0.5, 0.75, 1.0))
        # The lane cached Blender's PNG, bound to the saved receipt.
        status = self.runtime.state.job_session.result_previews.status("request", "image")
        cached = status.get("still").preview
        self.assertEqual((cached.media_type, cached.width, cached.height), ("image/png", 256, 128))
        self.assertTrue(cached.path.is_relative_to(self.root / "cache" / "result-previews"))
        # The temporary decode left the open file, its data and flags unchanged.
        self.assertEqual(self.data_counts(), self.counts)
        self.assertEqual(bpy.data.is_dirty, dirty)
        self.assertEqual(self.requests, [])
        self.assertEqual(self.downloads, [])
        calls = self.draw(view)
        self.assertIn(("icon", tile.icon_id or self.tiles._builtin("IMAGE_DATA"), ANY), calls)
        self.assertIn(("label", "Image (1)", "NONE"), calls)
        self.assertFalse([call for call in calls if call[0] == "operator"])

    def test_material_maps_show_base_color_first_and_at_most_four(self):
        maps = [
            (f"map-{role}", f"{role}.png", "image/png", png(8, 8), role)
            for role in ("normal", "height", "albedo", "metallic", "ao", "edge")
        ]
        with online_access(False):
            self.saved(maps)
            self.settle(
                lambda: all(
                    tile.status == "ready"
                    for tile in self.tiles.controller.tiles.get("request", (None,))
                    if tile
                )
            )
        captions = [tile.caption for tile in self.tiles.controller.tiles["request"]]
        self.assertEqual(captions, ["Albedo (3)", "Normal (1)", "Height (2)", "Metallic (4)"])

    def test_roughness_and_smoothness_maps_are_captioned_by_their_roles(self):
        # A roughness map from a 3D texture set once fell back to "Image (N)".
        maps = [
            (f"map-{role}", f"{role}.png", "image/png", png(8, 8), role)
            for role in ("roughness", "smoothness")
        ]
        with online_access(False):
            self.saved(maps)
            self.settle(lambda: [self.status(index=i) for i in range(2)] == ["ready"] * 2)
        captions = [tile.caption for tile in self.tiles.controller.tiles["request"]]
        self.assertEqual(captions, ["Roughness (1)", "Smoothness (2)"])

    def test_undecodable_saved_image_reports_a_failure_with_retry(self):
        with online_access(False):
            view = self.saved([("image", "result.png", "image/png", corrupt_png(64, 32))])
            self.settle(lambda: self.status() == "unavailable")
        tile = self.tile()
        self.assertTrue(tile.retry)
        self.assertIn("could not decode", tile.message)
        self.assertEqual(self.data_counts(), self.counts)
        calls = self.draw(view)
        self.assertIn(("icon", self.tiles._builtin("IMAGE_DATA"), ANY), calls)
        (retry,) = [call for call in calls if call[0] == "operator"]
        self.assertEqual(
            retry[1:4], ("scenario.retry_result_preview", "Retry preview (1)", "FILE_REFRESH")
        )
        self.assertEqual(
            retry[4],
            {
                "context_id": self.runtime.state.job_context_id,
                "request_id": "request",
                "asset_id": "image",
            },
        )

    def test_changed_cache_file_is_not_decoded_and_retry_prepares_it_again(self):
        with online_access(False):
            view = self.saved([("image", "result.png", "image/png", png(64, 32))])
            scheduler = self.runtime.state.job_session.result_previews
            # Let the lane cache the decoded still, but build no icon yet.
            self.tiles.controller.poll()
            ready = self.previews.PreviewState.READY

            def cached():
                self.module.reap_retired()
                self.tiles.controller._decode_one(scheduler)
                status = scheduler.status("request", "image")
                return status is not None and status.get("still").state == ready

            deadline = time.monotonic() + 30
            while not cached():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            path = scheduler.status("request", "image").get("still").preview.path
            path.write_bytes(png(64, 32, b"\xff\x00\x00\xff"))
            self.settle(lambda: self.status() == "unavailable")
            self.assertIn("changed or was removed", self.tile().message)
            args = {
                "context_id": self.runtime.state.job_context_id,
                "request_id": "request",
                "asset_id": "image",
            }
            self.assertEqual(bpy.ops.scenario.retry_result_preview(**args), {"FINISHED"})
            self.settle(lambda: self.status() == "ready")
        first = tuple(round(value, 2) for value in self.icon().image_pixels_float[:4])
        self.assertEqual(first, (0.25, 0.5, 0.75, 1.0))
        self.assertTrue(self.draw(view))

    # -- server stills --------------------------------------------------------

    def test_server_still_retries_a_first_access_redirect_then_shows_its_icon(self):
        url = f"{CDN}/thumb.png?signature=fixture"
        self.thumbnails["clip"], self.files[url] = url, png(320, 180)
        self.incomplete = 1
        with online_access(True):
            view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
            self.fast_polling()
            self.settle(lambda: self.status() == "waiting")
            self.assertIn("did not complete; retrying", self.tile().message)
            self.assertNotIn("signature", self.tile().message)
            calls = self.draw(view)
            self.assertIn(("icon", self.tiles._builtin("FILE_MOVIE"), ANY), calls)
            self.settle(lambda: self.status() == "ready")
        self.assertEqual(self.tile().caption, "Video (1)")
        self.assertEqual(tuple(self.icon().image_size), (256, 144))
        self.assertEqual([url for url, _ in self.downloads], [url, url])
        self.assertEqual({name for _, name in self.downloads}, {"ScenarioPreview"})
        self.assertEqual(self.data_counts(), self.counts)

    def test_missing_server_still_shows_a_placeholder_until_an_explicit_retry(self):
        with online_access(True):
            view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
            self.fast_polling(window=0.2)
            self.settle(lambda: self.status() == "unavailable")
            tile = self.tile()
            self.assertTrue(tile.retry)
            self.assertIn("no preview", tile.message)
            calls = self.draw(view)
            self.assertIn(("icon", self.tiles._builtin("FILE_MOVIE"), ANY), calls)
            self.assertIn("Retry preview (1)", [call[2] for call in calls if call[0] == "operator"])
            polls = len(self.requests)
            for _ in range(20):
                self.module.reap_retired()
                self.tiles.controller.poll()
            self.assertEqual(len(self.requests), polls)  # No polling after the window.
            url = f"{CDN}/late.png?signature=fixture"
            self.thumbnails["clip"], self.files[url] = url, png(64, 64)
            self.tiles.controller.retry(self.runtime.state.job_context_id, "request", "clip")
            self.settle(lambda: self.status() == "ready")
        self.assertEqual(tuple(self.icon().image_size), (64, 64))

    def test_offline_server_still_waits_without_contacting_scenario(self):
        with online_access(False):
            view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
            self.settle(lambda: self.status() == "offline")
        self.assertEqual(self.requests, [])
        texts = [call[1] for call in self.draw(view) if call[0] == "label"]
        # The caption under the placeholder, then the status wrapped to the sidebar.
        self.assertEqual(texts[0], "Video (1)")
        self.assertEqual(
            " ".join(texts[1:]), "Video (1): Preview paused while online access is disabled"
        )

    # -- panels and lifecycle ------------------------------------------------

    def test_jobs_generations_and_studio_draw_tiles_without_storage_reads(self):
        panels, studio = submodule("blender.panels"), submodule("blender.studio")
        with online_access(False):
            view = self.saved([("image", "result.png", "image/png", png(16, 16))])
            self.settle(lambda: self.status() == "ready")
            _, jobs, _, _ = draw_job_panels()
        icons = [call for call in jobs.mock_calls if call[0].endswith("template_icon")]
        self.assertTrue(icons)
        store = self.runtime.state.job_store
        refused = AssertionError("Store read in draw")
        # Generations draws the same tiles through draw_result, and Studio reuses
        # the panels; shared image rows no longer load draw-time thumbnails.
        result = MagicMock()
        studio_jobs = MagicMock()
        page = bpy.context.window_manager.scenario_studio_view
        previous = page.page
        self.addCleanup(setattr, page, "page", previous)
        page.page = "JOBS"
        with (
            patch.object(panels, "thumbnail") as thumbnail,
            patch.object(store, "get", side_effect=refused),
            patch.object(store, "records", side_effect=refused),
        ):
            panels.draw_result(result, view)
            studio.draw_view(studio_jobs, bpy.context, width=960)
        thumbnail.assert_not_called()
        for layout in (result, studio_jobs):
            drawn = [call for call in layout.mock_calls if call[0].endswith("template_icon")]
            self.assertTrue(drawn)

    def test_previews_follow_the_first_rows_each_panel_draws(self):
        records = submodule("core.jobs.records")
        rows = []
        for index in range(30):
            terminal = index % 2 == 0
            rows.append(
                records.JobRecord(
                    local_id=f"job-{index}",
                    lane="model",
                    kind="model",
                    model_id="model",
                    body={},
                    status="success" if terminal else "ready",
                    asset_ids=["asset"],
                    meta={
                        "shared_job": True,
                        "saved_state": "applied" if terminal else "ready",
                        "saved_revision": 1,
                    },
                )
            )
        rows.insert(
            0, records.JobRecord("prototype", "image", "image", "model", {}, status="success")
        )
        rows.insert(1, records.JobRecord("failed", "model", "model", "model", {}, status="failed"))
        self.runtime.state.jobs_view[:] = rows
        shown = [view.local_id for view in self.tiles.controller._shown()]
        # Generations counts every terminal row it lists, prototype and failed ones too.
        terminal = [f"job-{index}" for index in range(0, 20, 2)]
        active = [f"job-{index}" for index in range(1, 24, 2)]
        self.assertEqual(sorted(shown), sorted(terminal + active))

    def test_retirement_and_file_load_release_icons_and_ignore_late_status(self):
        with online_access(False):
            view = self.saved([("image", "result.png", "image/png", png(16, 16))])
            self.settle(lambda: self.status() == "ready")
            self.assertIsNotNone(self.tiles.controller._previews)
            self.tiles._file_load(None)
            self.assertEqual(self.tiles.controller.tiles, {})
            self.assertIsNone(self.tiles.controller._previews)
            self.assertEqual(self.draw(view), [])
            self.settle(lambda: self.status() == "ready")
            context = self.runtime.state.job_context_id
            self.runtime.state.retire_jobs()
            self.assertEqual(self.tiles.controller.tiles, {})
            self.assertIsNone(self.tiles.controller._previews)
            with self.assertRaises(self.tiles.RetryRefused):
                self.tiles.controller.retry(context, "request", "image")
            self.assertFalse(self.tiles.controller.poll())
            self.assertEqual(self.draw(view), [])

    def test_controller_belongs_to_the_main_thread(self):
        errors = []

        def run():
            try:
                self.tiles.controller.poll()
            except RuntimeError as error:
                errors.append(str(error))

        worker = threading.Thread(target=run)
        worker.start()
        worker.join()
        self.assertEqual(errors, ["Result previews belong to Blender's main thread"])
        self.assertIsInstance(self.tiles.controller, self.tiles.PreviewController)
