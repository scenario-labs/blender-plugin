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
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

import bpy
from helpers import draw_in_studio, draw_job_panels, online_access, submodule, temp_credentials

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


# Interface units of the sidebar that a status line under the tiles cannot use,
# measured in the physical desktop check (Blender 5.1.2, macOS Retina, sidebar
# with its category tabs) from the region's edges to the text after the line's
# icon and to the job box's right content edge. Wider lines would be clipped.
STATUS_MARGIN = 90
# The longest any wait here may take. Previews settle in well under a second on
# hosted CI, so this is ample; a bound per wait keeps tiles that never settle,
# as when no icon could be built on Windows, from adding up to the native
# runner's per-process timeout before unittest can report why.
WAIT_SECONDS = 10


class Layout:
    """Records draw calls, including nested rows, columns and boxes, in order.

    Rows and columns record into the same list and inherit ``enabled`` and
    ``scale_y``, as Blender's sublayouts do; an operator records whether its
    layout was enabled, then the layout's ``scale_y`` and ``ui_units_x``.
    """

    def __init__(self, calls=None, enabled=True, scale_y=1.0):
        self.calls = [] if calls is None else calls
        self.enabled = enabled
        self.scale_y = scale_y
        self.ui_units_x = 0.0

    def box(self):
        self.calls.append(("box",))
        return self

    def row(self, align=False):
        self.calls.append(("row",))
        return Layout(self.calls, self.enabled, self.scale_y)

    def column(self, align=False):
        self.calls.append(("column",))
        return Layout(self.calls, self.enabled, self.scale_y)

    def label(self, *, text, icon="NONE"):
        self.calls.append(("label", text, icon))

    def operator(self, idname, *, text="", icon="NONE", emboss=True):
        properties = {}
        self.calls.append(
            (
                "operator",
                idname,
                text,
                icon,
                properties,
                self.enabled,
                self.scale_y,
                self.ui_units_x,
            )
        )
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

    def settle(self, predicate, timeout=WAIT_SECONDS):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # The same main-thread entry points as the GUI timers.
            self.module.reap_retired()
            self.tiles.controller.poll()
            if predicate():
                return
            time.sleep(0.01)
        self.fail(f"Previews did not settle: {self.tiles.controller.tiles}")

    def cache_still(self, scheduler):
        """Run the lane until it caches the image's decoded still, building no icon.

        Returns the still's status; fails after ``WAIT_SECONDS``.
        """
        ready = self.previews.PreviewState.READY
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline:
            self.module.reap_retired()
            self.tiles.controller._decode_one(scheduler)
            status = scheduler.status("request", "image")
            if status is not None and status.get("still").state == ready:
                return status.get("still")
            time.sleep(0.01)
        raise self.failureException(
            f"The lane did not cache the still: {scheduler.status('request', 'image')}"
        )

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
        scheduler = self.runtime.state.job_session.result_previews
        cached = scheduler.status("request", "image").get("still").preview
        self.assertEqual((cached.media_type, cached.width, cached.height), ("image/png", 256, 128))
        # Spelled from the cache's canonical root, Windows' extended \\?\ namespace,
        # which the icon step compares with the scheduler's configured root.
        canonical = self.transfers._root(self.root / "cache" / "result-previews")
        self.assertTrue(cached.path.is_relative_to(canonical))
        self.assertTrue(self.previews.in_cache(cached.path, scheduler.root))
        # The temporary decode left the open file, its data and flags unchanged.
        self.assertEqual(self.data_counts(), self.counts)
        self.assertEqual(bpy.data.is_dirty, dirty)
        self.assertEqual(self.requests, [])
        self.assertEqual(self.downloads, [])
        calls = self.draw(view)
        self.assertIn(("icon", tile.icon_id or self.tiles._builtin("IMAGE_DATA"), ANY), calls)
        self.assertIn(("label", "(1) Image", "NONE"), calls)
        self.assertFalse([call for call in calls if call[0] == "operator"])

    def ready_page(self, count=4):
        tiles = self.tiles.controller.tiles.get("request", ())
        return len(tiles) == count and all(tile.status == "ready" for tile in tiles)

    def six_maps(self, settled=None):
        maps = [
            (f"map-{role}", f"{role}.png", "image/png", png(8, 8), role)
            for role in ("normal", "height", "albedo", "metallic", "ao", "edge")
        ]
        view = self.saved(maps)
        self.settle(settled or self.ready_page)
        return view

    def pager(self, view):
        """The drawn arrows as (text, enabled, properties) and the range label."""
        calls = self.draw(view)
        arrows = [
            (call[2], call[5], call[4])
            for call in calls
            if call[0] == "operator" and call[1] == "scenario.page_result_previews"
        ]
        labels = [call[1] for call in calls if call[0] == "label" and " of " in call[1]]
        return arrows, labels

    def page(self, direction, request_id="request", context_id=None):
        context_id = context_id or self.runtime.state.job_context_id
        return bpy.ops.scenario.page_result_previews(
            context_id=context_id, request_id=request_id, direction=direction
        )

    def captions(self):
        return [tile.caption for tile in self.tiles.controller.tiles["request"]]

    def test_material_maps_show_base_color_first_four_at_a_time(self):
        with online_access(False):
            view = self.six_maps()
            self.assertEqual(
                self.captions(), ["Albedo (3)", "Normal (1)", "Height (2)", "Metallic (4)"]
            )
            scheduler = self.runtime.state.job_session.result_previews
            # Only the drawn page is requested; the rest waits for the pager.
            self.assertIsNone(scheduler.status("request", "map-ao"))
            arrows, labels = self.pager(view)
            context = {"context_id": self.runtime.state.job_context_id, "request_id": "request"}
            self.assertEqual(
                arrows,
                [
                    ("\u2039", False, {**context, "direction": "PREVIOUS"}),
                    ("\u203a", True, {**context, "direction": "NEXT"}),
                ],
            )
            self.assertEqual(labels, ["1-4 of 6"])
            # The arrows sit around the tiles: first and last in the tile row.
            calls = self.draw(view)
            drawn = [call for call in calls if call[0] in ("icon", "operator")]
            self.assertEqual([call[0] for call in drawn], ["operator", *["icon"] * 4, "operator"])
            self.assertEqual(self.page("NEXT"), {"FINISHED"})
            # The last page ends at the last result: ranks 3 to 6.
            self.assertEqual(self.captions(), ["Height (2)", "Metallic (4)", "AO (5)", "Edge (6)"])
            self.assertIsNotNone(scheduler.status("request", "map-ao"))
            self.settle(self.ready_page)
            arrows, labels = self.pager(view)
            self.assertEqual(
                [(text, enabled) for text, enabled, _ in arrows],
                [
                    ("\u2039", True),
                    ("\u203a", False),
                ],
            )
            self.assertEqual(labels, ["3-6 of 6"])
            self.assertEqual(self.page("PREVIOUS"), {"FINISHED"})
            self.assertEqual(
                self.captions(), ["Albedo (3)", "Normal (1)", "Height (2)", "Metallic (4)"]
            )
            self.assertEqual(self.pager(view)[1], ["1-4 of 6"])
        self.assertEqual(self.requests, [])
        self.assertEqual(self.data_counts(), self.counts)

    def test_paging_clamps_at_either_end_and_refuses_stale_requests(self):
        with online_access(False):
            view = self.six_maps()
            # Already on the first page: nothing changes.
            self.assertEqual(self.page("PREVIOUS"), {"CANCELLED"})
            self.assertEqual(self.pager(view)[1], ["1-4 of 6"])
            self.assertEqual(self.page("NEXT"), {"FINISHED"})
            self.assertEqual(self.page("NEXT"), {"CANCELLED"})
            self.assertEqual(self.pager(view)[1], ["3-6 of 6"])
            with self.assertRaises(TypeError):
                self.page("LAST")  # Only the previous or next page.
            with self.assertRaises(RuntimeError):
                self.page("NEXT", context_id="another-connection")
            with self.assertRaises(RuntimeError):
                self.page("NEXT", request_id="unknown")
            with self.assertRaises(self.tiles.PageRefused):
                self.tiles.controller.page("another-connection", "request", 1)
            with self.assertRaises(ValueError):
                self.tiles.controller.page(self.runtime.state.job_context_id, "request", 2)
            self.assertEqual(self.pager(view)[1], ["3-6 of 6"])

    def test_four_or_fewer_results_draw_no_pager(self):
        maps = [
            (f"map-{role}", f"{role}.png", "image/png", png(8, 8), role)
            for role in ("normal", "height", "albedo", "metallic")
        ]
        with online_access(False):
            view = self.saved(maps)
            self.settle(self.ready_page)
            self.assertEqual(self.pager(view), ([], []))
            self.assertNotIn("request", self.tiles.controller.pages)
            self.assertEqual(self.page("NEXT"), {"CANCELLED"})

    @staticmethod
    def reread(controller):
        """Make the next poll read the saved job again, as a new saved revision does."""
        controller._jobs["request"] = replace(controller._jobs["request"], revision=-1)

    def test_the_page_resets_when_the_results_change_or_the_connection_retires(self):
        with online_access(False):
            view = self.six_maps()
            self.assertEqual(self.page("NEXT"), {"FINISHED"})
            controller = self.tiles.controller
            targets = self.tiles.tile_targets

            def without_edge(record):
                return tuple(target for target in targets(record) if target.label != "Edge")

            # A saved revision whose previewable results differ: five maps now.
            with patch.object(self.tiles, "tile_targets", side_effect=without_edge):
                self.reread(controller)
                self.settle(lambda: self.pager(view)[1] == ["1-4 of 5"])
                self.assertEqual(
                    self.captions(), ["Albedo (3)", "Normal (1)", "Height (2)", "Metallic (4)"]
                )
            self.reread(controller)
            self.settle(lambda: self.pager(view)[1] == ["1-4 of 6"])
            self.assertEqual(self.page("NEXT"), {"FINISHED"})
            self.assertEqual(self.pager(view)[1], ["3-6 of 6"])
            self.runtime.state.retire_jobs()
            self.assertEqual(controller.pages, {})
            self.assertEqual(dict(controller._offsets.items()), {})
            view = self.runtime.inspect_model_jobs().views["request"]
            self.settle(self.ready_page)
            self.assertEqual(self.pager(view)[1], ["1-4 of 6"])

    def test_drawing_a_paged_row_reads_and_changes_nothing(self):
        with online_access(False):
            view = self.six_maps()
            self.assertEqual(self.page("NEXT"), {"FINISHED"})
            self.settle(self.ready_page)
            controller = self.tiles.controller
            before = (
                dict(controller.tiles),
                dict(controller.pages),
                dict(controller._offsets.items()),
                dict(controller._jobs),
            )
            # self.draw refuses file and store access while drawing.
            for _ in range(3):
                self.assertTrue(self.draw(view))
            after = (
                dict(controller.tiles),
                dict(controller.pages),
                dict(controller._offsets.items()),
                dict(controller._jobs),
            )
            self.assertEqual(before, after)

    def test_a_failed_icon_keeps_its_retry_while_its_job_is_paged_away_and_back(self):
        # Adapted from a review finding: paging a failed icon's result away
        # forgot the failure, so paging back verified the file again.
        verified, checks = self.tiles._verified, []

        def normal_changed(preview, root):
            status = self.runtime.state.job_session.result_previews.status("request", "map-normal")
            if status is not None and preview == status.get("still").preview:
                checks.append(preview)
                return None  # As when its cache file changed.
            return verified(preview, root)

        def normal_failed():
            tiles = self.tiles.controller.tiles.get("request", ())
            return [tile.status for tile in tiles] == ["ready", "unavailable", "ready", "ready"]

        with online_access(False):
            with patch.object(self.tiles, "_verified", side_effect=normal_changed):
                view = self.six_maps(normal_failed)
                failed = self.tile(index=1)
                self.assertEqual((failed.caption, failed.retry), ("Normal (1)", True))
                self.assertIn("changed or was removed", failed.message)
                self.assertEqual(len(checks), 1)
                self.assertEqual(self.page("NEXT"), {"FINISHED"})
                self.assertNotIn("Normal (1)", self.captions())
                self.settle(self.ready_page)
                self.assertEqual(self.page("PREVIOUS"), {"FINISHED"})
                # Back at once, before a tick could build an icon.
                self.assertEqual(self.tile(index=1), failed)
                self.settle(normal_failed)
                self.assertEqual(self.tile(index=1), failed)
                self.assertEqual(len(checks), 1)  # Its file was not verified again.
            args = {
                "context_id": self.runtime.state.job_context_id,
                "request_id": "request",
                "asset_id": "map-normal",
            }
            self.assertEqual(bpy.ops.scenario.retry_result_preview(**args), {"FINISHED"})
            self.settle(self.ready_page)
            self.assertEqual(self.pager(view)[1], ["1-4 of 6"])
        self.assertEqual(self.requests, [])
        self.assertEqual(self.data_counts(), self.counts)

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

    def test_tile_captions_put_the_number_first_so_a_narrow_column_keeps_it(self):
        # In the sidebar at its default width, "Model (1)" and "Model (2)" were
        # clipped to "Model ..." and lost the number their controls show.
        import blf

        assets = [
            ("glb", "model.glb", "model/gltf-binary", b"glTF" + b"\x00" * 16),
            ("obj", "model.obj", "model/obj", b"o cube\n"),
            ("albedo", "albedo.png", "image/png", png(8, 8), "albedo"),
            ("normal", "normal.png", "image/png", png(8, 8), "normal"),
        ]
        settled = ["offline", "ready", "offline", "ready"]  # Server stills wait offline.
        with online_access(False):
            view = self.saved(assets)
            self.settle(lambda: [self.status(index=i) for i in range(4)] == settled)
        tiles = self.tiles.controller.tiles["request"]
        # Status lines name results as the saved-job controls do.
        self.assertEqual(
            [tile.caption for tile in tiles], ["Model (1)", "Albedo (3)", "Model (2)", "Normal (4)"]
        )
        calls = self.draw(view)
        drawn = [
            (call[2], following[1])
            for call, following in zip(calls, calls[1:], strict=False)
            if call[0] == "icon" and following[0] == "label"
        ]
        self.assertEqual(
            [title for _, title in drawn], ["(1) Model", "(3) Albedo", "(2) Model", "(4) Normal"]
        )
        texts = [call[1] for call in calls if call[0] == "label"][len(drawn) :]
        self.assertEqual(
            " ".join(texts),
            "Model\u00a0(1), Model\u00a0(2): Preview paused while online access is disabled",
        )
        # Blender keeps the start of a label that does not fit and clips the
        # rest, so the number survives while it fits under the tile's icon in
        # the UI font: 20 units per icon scale step at UI scale 1.
        blf.size(0, bpy.context.preferences.ui_styles[0].widget.points)
        for scale, title in drawn:
            number = title.split(" ", 1)[0]
            self.assertLess(blf.dimensions(0, f"{number}…")[0], 20 * scale, title)
        # The smallest tiles: a paged row's in a narrow region.
        self.assertLess(blf.dimensions(0, "(99)…")[0], 20 * self.tiles.PAGED_MIN_SCALE)

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
            path = self.cache_still(scheduler).preview.path
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

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX named pipes")
    def test_a_cache_file_replaced_by_a_named_pipe_never_blocks_the_main_thread(self):
        # Opening a named pipe for reading waits for a writer unless it is
        # nonblocking, which would freeze Blender's main thread in the timer.
        with online_access(False):
            view = self.saved([("image", "result.png", "image/png", png(64, 32))])
            scheduler = self.runtime.state.job_session.result_previews
            self.tiles.controller.poll()
            preview = self.cache_still(scheduler).preview
            preview.path.unlink()
            os.mkfifo(preview.path, 0o600)
            result = []
            reader = threading.Thread(
                target=lambda: result.append(self.tiles._verified(preview, scheduler.root)),
                daemon=True,
            )
            reader.start()
            reader.join(5)
            if reader.is_alive():
                # Release the blocked reader so the failure leaves no thread behind.
                os.close(os.open(preview.path, os.O_WRONLY | os.O_NONBLOCK))
                reader.join(5)
                self.fail("Verifying a cached preview blocked on a named pipe")
            self.assertEqual(result, [None])
            self.settle(lambda: self.status() == "unavailable")
            self.assertIn("changed or was removed", self.tile().message)
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
        self.assertEqual(texts[0], "(1) Video")
        self.assertEqual(
            " ".join(texts[1:]), "Video\u00a0(1): Preview paused while online access is disabled"
        )

    # -- panels and lifecycle ------------------------------------------------

    def tile_calls(self, view, width, scale, popup=None, studio=None):
        """Draw calls of the tiles in a region `width` pixels wide or a popup `popup`
        pixels wide, drawn inside Studio's view `studio` interface units wide if given."""
        context = SimpleNamespace(
            region=SimpleNamespace(width=width),
            region_popup=None if popup is None else SimpleNamespace(width=popup),
            preferences=SimpleNamespace(
                system=SimpleNamespace(ui_scale=scale),
                ui_styles=bpy.context.preferences.ui_styles,
            ),
        )
        layout = Layout()
        with patch.object(self.tiles, "bpy", SimpleNamespace(context=context, types=bpy.types)):
            if studio is None:
                self.tiles.draw(layout, view)
            else:
                draw_in_studio(lambda: self.tiles.draw(layout, view), studio)
        return layout.calls

    def status_lines(self, view, width, scale, popup=None, studio=None):
        """Status labels below the tiles."""
        calls = self.tile_calls(view, width, scale, popup, studio)
        shown = sum(call[0] == "icon" for call in calls)
        return [call[1] for call in calls if call[0] == "label"][shown:]

    def offline_models(self):
        """A saved GLB and OBJ waiting offline, and their one status line's text."""
        assets = [
            ("glb", "model.glb", "model/gltf-binary", b"glTF" + b"\x00" * 16),
            ("obj", "model.obj", "model/obj", b"o cube\n"),
        ]
        with online_access(False):
            view = self.saved(assets)
            self.settle(lambda: [self.status(index=i) for i in range(2)] == ["offline"] * 2)
        # A no-break space keeps each result's name with its number.
        return (
            view,
            "Model\u00a0(1), Model\u00a0(2): Preview paused while online access is disabled",
        )

    def assert_fits(self, lines, message, pixels, scale):
        import blf

        self.assertEqual(" ".join(lines), message)  # Breaks only at ordinary spaces.
        blf.size(0, bpy.context.preferences.ui_styles[0].widget.points * scale)
        for line in lines:
            self.assertLessEqual(blf.dimensions(0, line)[0], pixels, line)

    def test_status_lines_wrap_by_the_width_blender_measures(self):
        # A desktop check at UI scale 1.0 on a Retina display (interface scale 2,
        # a 561 px sidebar) found waveform status text, wrapped with the same
        # 7 units per character estimate, breaking at about half the box.
        view, message = self.offline_models()
        lines = self.status_lines(view, 561, 2.0)
        self.assert_fits(lines, message, 561 - STATUS_MARGIN * 2, 2.0)
        # A popup's context region is the one it was invoked from, such as the
        # 3D View header, which spans the area; Blender sized this popup's region.
        lines = self.status_lines(view, 2400, 2.0, popup=600)
        self.assertGreater(len(lines), 1)
        self.assert_fits(lines, message, 600 - STATUS_MARGIN * 2, 2.0)
        self.assertEqual(self.status_lines(view, 2400, 2.0), [message])

    def test_studio_wraps_status_and_sizes_icons_from_the_requested_width_on_its_first_draw(self):
        # Blender builds a popup's layout before it sizes the popup's region, so
        # Studio's first draw finds that region 0 px wide; a refresh finds it
        # sized to the requested width plus the popup's margins.
        view, message = self.offline_models()
        scale, requested = 2.0, 300
        first = self.tile_calls(view, 2400, scale, popup=0, studio=requested)
        refreshed = self.tile_calls(
            view, 2400, scale, popup=(requested + 24) * scale, studio=requested
        )
        self.assertEqual(first, refreshed)
        # Two tiles in 300 units take the largest icon scale, not the 2.5 minimum.
        self.assertEqual([call[2] for call in first if call[0] == "icon"], [5.0, 5.0])
        lines = self.status_lines(view, 2400, scale, popup=0, studio=requested)
        self.assertGreater(len(lines), 1)
        self.assertLessEqual(len(lines), 3, lines)
        self.assert_fits(lines, message, (requested - STATUS_MARGIN) * scale, scale)

    def tile_sizes(self, view, width, scale, popup=None, studio=None):
        """The icon scales of a row drawn as tile_calls draws it, and its pager
        arrows as (units wide, scale_y)."""
        calls = self.tile_calls(view, width, scale, popup, studio)
        icons = [call[2] for call in calls if call[0] == "icon"]
        arrows = [
            (call[7], call[6])
            for call in calls
            if call[0] == "operator" and call[1] == "scenario.page_result_previews"
        ]
        return icons, arrows

    def assert_numbers_fit(self, icon_scale, titles):
        """Each caption's number with an ellipsis fits under an icon of that scale."""
        import blf

        blf.size(0, bpy.context.preferences.ui_styles[0].widget.points)
        for title in titles:
            number = title.split(" ", 1)[0]
            self.assertLess(blf.dimensions(0, f"{number}…")[0], 20 * icon_scale, title)

    def test_a_paged_row_fits_the_default_sidebar_so_its_arrows_are_as_tall_as_its_icons(self):
        # A desktop check found the arrows about 1.65 times as tall as the icons
        # in the sidebar at its default width, 561 px at UI scale 1.0 and 1122 px
        # at 2.0 on a Retina display, 280.5 interface units either way. The paged
        # row's icon scale was raised to 2.5, so the row was wider than its
        # region: Blender narrowed every item, but not the arrows' height.
        with online_access(False):
            view = self.six_maps()
        titles = [tile.title for tile in self.tiles.controller.tiles["request"]]
        for pixels, scale in ((561, 2.0), (1122, 4.0)):
            with self.subTest(pixels=pixels, ui_scale=scale):
                icons, arrows = self.tile_sizes(view, pixels, scale)
                self.assertEqual(len(icons), 4)
                icon_scale = icons[0]
                self.assertEqual(icons, [icon_scale] * 4)
                self.assertLess(icon_scale, 2.5)
                # Blender's row in interface units: about 22 per icon scale step
                # for each tile with its spacing, 24 for each one-unit arrow and
                # 60 for the panel and job box margins. An unpaged row of four
                # 2.5 icons, 280 units, fitted this sidebar on the desktop.
                needed = 4 * 22 * icon_scale + 2 * 24 + 60
                self.assertLessEqual(round(needed, 6), pixels / scale)
                self.assertEqual(arrows, [(1.0, icon_scale), (1.0, icon_scale)])
                self.assert_numbers_fit(icon_scale, titles)

    def test_a_paged_row_in_a_narrow_sidebar_keeps_its_arrows_as_tall_as_its_smallest_icons(self):
        with online_access(False):
            view = self.six_maps()
        # 200 and 150 interface units, both narrower than a paged row of the
        # smallest icons; those icons still hold a two-digit caption number.
        sizes = [self.tile_sizes(view, pixels, 2.0) for pixels in (400, 300)]
        self.assertEqual(sizes[0], sizes[1])
        icons, arrows = sizes[0]
        smallest = icons[0]
        self.assertEqual(icons, [smallest] * 4)
        self.assertLess(smallest, 2.5)
        self.assertEqual(arrows, [(1.0, smallest), (1.0, smallest)])
        self.assert_numbers_fit(smallest, ["(99) Metallic"])

    def test_four_results_keep_the_unpaged_icon_scale_and_its_minimum(self):
        maps = [
            (f"map-{role}", f"{role}.png", "image/png", png(8, 8), role)
            for role in ("normal", "height", "albedo", "metallic")
        ]
        with online_access(False):
            view = self.saved(maps)
            self.settle(self.ready_page)
        # The default sidebar fits four tiles of about 2.5 without arrows:
        # (280.5 - 60) / (22 * 4).
        for pixels, scale in ((561, 2.0), (1122, 4.0)):
            with self.subTest(pixels=pixels, ui_scale=scale):
                icons, arrows = self.tile_sizes(view, pixels, scale)
                self.assertEqual(arrows, [])
                self.assertEqual(len(icons), 4)
                for drawn in icons:
                    self.assertAlmostEqual(drawn, (280.5 - 60) / 88)
                    self.assertGreaterEqual(drawn, 2.5)
        # A narrower sidebar keeps an unpaged row's 2.5 minimum.
        self.assertEqual(self.tile_sizes(view, 400, 2.0), ([2.5] * 4, []))

    def test_a_paged_row_in_a_wide_region_keeps_its_icon_scale(self):
        # Studio and a widened sidebar already fitted a paged row beside its
        # arrows on the desktop; their icons keep the size they had.
        with online_access(False):
            view = self.six_maps()
        for scale in (2.0, 4.0):
            with self.subTest(studio=960, ui_scale=scale):
                icons, arrows = self.tile_sizes(view, 2400, scale, popup=0, studio=960)
                self.assertEqual(icons, [5.0] * 4)
                self.assertEqual(arrows, [(1.0, 5.0), (1.0, 5.0)])
        # The sidebar widened to 861 px at UI scale 1.0 on a Retina display.
        icons, arrows = self.tile_sizes(view, 861, 2.0)
        expected = (861 / 2.0 - 60 - 2 * 24) / (22 * 4)
        self.assertGreater(expected, 2.5)
        for drawn in icons:
            self.assertAlmostEqual(drawn, expected)
        self.assertEqual(len(icons), 4)
        self.assertEqual([units for units, _ in arrows], [1.0, 1.0])
        for _, height in arrows:
            self.assertAlmostEqual(height, expected)

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

    def test_jobs_generations_and_studio_draw_the_same_pager(self):
        panels, studio = submodule("blender.panels"), submodule("blender.studio")
        with online_access(False):
            view = self.six_maps()
            self.assertEqual(self.page("NEXT"), {"FINISHED"})
            _, jobs, _, _ = draw_job_panels()
            result, active, studio_jobs = MagicMock(), MagicMock(), MagicMock()
            page = bpy.context.window_manager.scenario_studio_view
            previous = page.page
            self.addCleanup(setattr, page, "page", previous)
            page.page = "JOBS"
            store = self.runtime.state.job_store
            refused = AssertionError("Store read in draw")
            with (
                patch.object(store, "get", side_effect=refused),
                patch.object(store, "records", side_effect=refused),
            ):
                panels.draw_result(result, view)
                panels.draw_active_job(active, view)
                studio.draw_view(studio_jobs, bpy.context, width=960)
        for name, layout in (
            ("jobs", jobs),
            ("generations", result),
            ("active", active),
            ("studio", studio_jobs),
        ):
            with self.subTest(surface=name):
                arrows = [
                    call
                    for call in layout.mock_calls
                    if call[0].endswith("operator")
                    and call.args[:1] == ("scenario.page_result_previews",)
                ]
                self.assertEqual([call.kwargs["text"] for call in arrows], ["\u2039", "\u203a"])
                labels = [
                    call.kwargs.get("text")
                    for call in layout.mock_calls
                    if call[0].endswith("label")
                ]
                self.assertIn("3-6 of 6", labels)

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

    def test_a_refused_preview_request_is_made_again_later(self):
        with online_access(False):
            self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
            scheduler = self.runtime.state.job_session.result_previews
            request = scheduler.request
            refusal = self.previews.PreviewError(
                "Too many result previews are pending; try again shortly"
            )
            calls, refusals = [], [refusal]

            def full_then_open(*args, **kwargs):
                calls.append(args)
                if refusals:
                    raise refusals.pop()
                return request(*args, **kwargs)

            controller = self.tiles.controller
            with patch.object(scheduler, "request", side_effect=full_then_open):
                controller.poll()
                (tile,) = controller.tiles["request"]
                self.assertEqual(
                    (tile.caption, tile.status, tile.message),
                    ("Video (1)", "waiting", str(refusal)),
                )
                # Not due yet: the refusal is shown, not requested on every tick.
                controller.poll()
                self.assertEqual(len(calls), 1)
                job = controller._jobs["request"]
                self.assertEqual(job.attempts, 1)
                self.assertAlmostEqual(
                    job.retry_at - time.monotonic(), self.tiles.REQUEST_RETRY[0], delta=1.0
                )
                controller._jobs["request"] = replace(job, retry_at=0.0)
                self.settle(lambda: self.status() == "offline")
            self.assertEqual(len(calls), 2)
        self.assertEqual(self.requests, [])

    def test_a_refused_later_page_keeps_ready_tiles_and_the_page(self):
        # Adapted from review findings: refusing the next page's request
        # replaced the job's ready tiles with one note and reset its pager.
        with online_access(False):
            view = self.six_maps()
            scheduler = self.runtime.state.job_session.result_previews
            request = scheduler.request
            refusal = self.previews.PreviewError(
                "Too many result previews are pending; try again shortly"
            )
            calls, refusals = [], [refusal]

            def full_then_open(*args, **kwargs):
                calls.append(tuple(kwargs["asset_ids"]))
                if refusals:
                    raise refusals.pop()
                return request(*args, **kwargs)

            controller = self.tiles.controller
            with patch.object(scheduler, "request", side_effect=full_then_open):
                self.assertEqual(self.page("NEXT"), {"FINISHED"})
                self.assertEqual(calls, [("map-ao", "map-edge")])
                tiles = controller.tiles["request"]
                self.assertEqual(
                    [(tile.caption, tile.status, tile.message) for tile in tiles],
                    [
                        ("Height (2)", "ready", ""),
                        ("Metallic (4)", "ready", ""),
                        ("AO (5)", "waiting", str(refusal)),
                        ("Edge (6)", "waiting", str(refusal)),
                    ],
                )
                self.assertEqual(self.pager(view)[1], ["3-6 of 6"])
                # Not due yet: the next ticks request nothing and keep the page.
                controller.poll()
                controller.poll()
                self.assertEqual(len(calls), 1)
                self.assertEqual(self.pager(view)[1], ["3-6 of 6"])
                job = controller._jobs["request"]
                controller._jobs["request"] = replace(job, retry_at=0.0)
                self.settle(self.ready_page)
            self.assertEqual(len(calls), 2)
            self.assertEqual(self.captions(), ["Height (2)", "Metallic (4)", "AO (5)", "Edge (6)"])
            self.assertEqual(self.pager(view)[1], ["3-6 of 6"])
        self.assertEqual(self.requests, [])

    def test_a_decoded_copy_the_lane_refuses_is_the_ticks_only_decode(self):
        # Adapted from a review finding: when the lane refused a decoded image
        # copy, the same tick also decoded an icon.
        workers = submodule("core.jobs.workers")
        controller = self.tiles.controller
        with online_access(False):
            self.saved(
                [
                    ("first", "first.png", "image/png", png(16, 16)),
                    ("second", "second.png", "image/png", png(8, 8)),
                ]
            )
            scheduler = self.runtime.state.job_session.result_previews
            issued = scheduler.decode_requests

            def first_only():
                return tuple(request for request in issued() if request.key.asset_id == "first")

            # The second copy waits while the first result's icon is built.
            with patch.object(scheduler, "decode_requests", side_effect=first_only):
                self.settle(
                    lambda: (
                        self.status(index=0) == "ready"
                        and any(request.key.asset_id == "second" for request in issued())
                    )
                )
            controller._icons.clear()  # Its icon is built again, as after trimming.
            decodes, decode = [], self.tiles.decode

            def counted(*args, **kwargs):
                decodes.append(args[0])
                return decode(*args, **kwargs)

            refusal = workers.WorkerError("The preview lane is full")
            with (
                patch.object(self.tiles, "decode", side_effect=counted),
                patch.object(scheduler, "finish_decode", side_effect=refusal),
            ):
                controller.poll()
            # The second copy was decoded; the first icon waits for another tick.
            self.assertEqual(len(decodes), 1)
            self.assertEqual(self.status(index=0), "loading")
            self.settle(lambda: self.ready_page(2))
        self.assertEqual(self.requests, [])

    def test_a_failed_redraw_keeps_the_preview_timer_running(self):
        controller = self.tiles.controller
        with (
            patch.object(controller, "poll", return_value=True),
            patch.object(self.tiles, "_redraw", side_effect=RuntimeError("no screen")),
            self.assertLogs("scenario", "WARNING"),
        ):
            self.assertEqual(self.tiles._tick(), controller.interval())

    def test_controller_belongs_to_the_main_thread(self):
        errors = []

        def run():
            try:
                self.tiles.controller.poll()
            except RuntimeError as error:
                errors.append(str(error))

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(WAIT_SECONDS)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, ["Result previews belong to Blender's main thread"])
        self.assertIsInstance(self.tiles.controller, self.tiles.PreviewController)
