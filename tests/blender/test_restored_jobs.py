# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved jobs listed after a restart offer the result tools they offered before it.

Finished Image, Render Image, Video and 3D jobs are saved through the real store
with private offline bytes. Their views are first projected as a submission
leaves them in its session, an Image job after its automatic import listed its
files, and drawn through a recording layout. The runtime is then reset as a
restart would, the store lists the same jobs again and they are drawn again.
Nothing contacts Scenario.
"""

import hashlib
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import online_access, submodule, temp_credentials
from test_result_grid import Recorder
from test_result_preview_tiles import MP4, png

GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 24
PROMPT = "Mossy stone well at dawn"
# request ID -> (lane, model ID, catalog name, result file name, media type, bytes)
JOBS = {
    "still": ("image", "model_fixture-image", "Fixture Image", "000-still.png", "image/png"),
    "render": (
        "render_image",
        "model_fixture-render",
        "Fixture Render",
        "000-render.png",
        "image/png",
    ),
    "clip": ("video", "model_fixture-video", "Fixture Video", "000-clip.mp4", "video/mp4"),
    "mesh": ("3d", "model_fixture-mesh", "Fixture Mesh", "000-mesh.glb", "model/gltf-binary"),
}
# A 2:1 still keeps the same World offer whether or not its size was read yet.
DATA = {"image/png": png(16, 8), "video/mp4": MP4, "model/gltf-binary": GLB}
# Rows about the job rather than its result: collapse, details, copy and previews.
IDENTITY = frozenset(
    {
        "scenario.toggle_result",
        "scenario.result_details",
        "scenario.copy_text",
        "scenario.error_details",
        "scenario.page_result_previews",
        "scenario.retry_result_preview",
    }
)
WAIT_SECONDS = 10


class RestoredJobTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.runtime = submodule("blender.runtime")
        self.panels = submodule("blender.panels")
        self.model_jobs = submodule("blender.model_jobs")
        self.handoff = submodule("blender.first_frame_handoff")
        self.module = submodule("blender.job_session")
        self.records = submodule("core.jobs.records")
        self.storemod = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.lane_kind = submodule("core.api.catalog").LANE_KIND
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(False))
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
            raise AssertionError("Listing and drawing saved jobs never contacts Scenario")

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

    def cleanup(self):
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    def catalog(self):
        """The loaded catalog's names, which drawing reads; no model details."""
        self.runtime.state.records.update(
            {model: SimpleNamespace(name=name) for _, model, name, *_ in JOBS.values()}
        )

    def save(self, request_id, *, lane=None, applied=False):
        """A finished job whose receipts match private local bytes; its file path."""
        m = self.storemod
        _, model, _, name, media_type = JOBS[request_id]
        data = DATA[media_type]
        store = self.runtime.ensure_job_store()
        session = self.runtime.ensure_job_session()
        origin = m.JobOrigin("file", "scene", "revision")
        current = store.create(
            m.JobIntent(
                request_id,
                store.scope,
                origin,
                "model",
                model,
                "a" * 64,
                "b" * 64,
                "1.5",
                lane=lane,
            )
        )
        for state in (m.JobState.SUBMITTING, m.JobState.REMOTE, m.JobState.SUCCEEDED):
            current = store.transition(
                request_id,
                expected_revision=current.revision,
                state=state,
                remote_job_id=f"remote-{request_id}" if state == m.JobState.REMOTE else None,
            )
        manifest = (m.ResultAsset(f"asset-{request_id}", name, media_type, len(data)),)
        current = store.set_results(request_id, manifest, expected_revision=current.revision)
        current = store.transition(
            request_id, expected_revision=current.revision, state=m.JobState.DOWNLOADING
        )
        directory = session._coordinator._results._directory(current)
        (directory / name).write_bytes(data)
        receipt = self.transfers.DownloadedResult(name, len(data), hashlib.sha256(data).hexdigest())
        current = store.record_download(
            request_id, manifest[0].asset_id, receipt, expected_revision=current.revision
        )
        current = store.transition(
            request_id, expected_revision=current.revision, state=m.JobState.READY
        )
        if applied:
            # An Image lane job imported automatically into its scene.
            current = store.transition(
                request_id,
                expected_revision=current.revision,
                state=m.JobState.APPLYING,
                application_origin=origin,
            )
            store.transition(
                request_id, expected_revision=current.revision, state=m.JobState.APPLIED
            )
        return str(directory / name)

    def submitted(self, jobs, request_id, files=()):
        """The view a submission leaves in its session, as ModelJobs.submit builds it."""
        lane, model, name, *_ = JOBS[request_id]
        view = self.records.JobRecord(
            local_id=request_id,
            lane=lane,
            kind=self.lane_kind[lane],
            model_id=model,
            body={"prompt": PROMPT},
            status="prepared",
            cu_cost=1.5,
            meta={"prompt": PROMPT, "model_name": name, "shared_job": True},
        )
        jobs.views[request_id] = view
        jobs._bindings[request_id] = self.model_jobs.JobBinding(bpy.context.scene.session_uid, lane)
        if lane == "image":
            # Its automatic import applied the result and listed the verified file.
            jobs._automatic_application.add(request_id)
            view.files = list(files)
        return view

    def restart(self):
        """Forget every session memory; the saved store and files remain on disk."""
        self.runtime.state.reset()
        self.module.reap_retired()
        self.assertIsNone(self.runtime.state.model_jobs)
        # The pump's catalog step selects the connection, then lists its saved jobs.
        self.runtime.ensure_catalog()
        self.catalog()
        self.assertTrue(self.runtime.show_saved_jobs())
        return self.runtime.state.model_jobs

    def settle(self, predicate):
        """Run the main-thread maintenance a GUI tick runs until ``predicate`` holds."""
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline:
            self.module.reap_retired()
            self.runtime.state.model_jobs.poll()
            if predicate():
                return True
            time.sleep(0.01)
        return False

    def tools(self, view):
        """The row's header (text, icon) and every result control it draws, in order."""
        layout = Recorder()
        self.panels.draw_result(layout, view)
        header = next(call for call in layout.calls if call.name == "label")
        controls = [
            (call.args[0], call.kwargs.get("text", ""))
            for call in layout.calls
            if call.name.startswith("operator") and call.args[0] not in IDENTITY
        ]
        return (header.kwargs["text"], header.kwargs["icon"]), controls

    def test_restarted_jobs_offer_the_tools_they_offered_before(self):
        self.catalog()
        files = {
            request_id: self.save(
                request_id, lane=JOBS[request_id][0], applied=request_id == "still"
            )
            for request_id in JOBS
        }
        jobs = self.runtime.ensure_model_jobs()
        views = {
            request_id: self.submitted(jobs, request_id, [files[request_id]]) for request_id in JOBS
        }
        jobs.poll()
        before = {request_id: self.tools(view) for request_id, view in views.items()}
        restored = self.restart()
        self.assertTrue(self.settle(lambda: restored.views["still"].files))
        for request_id, (lane, _, name, *_) in JOBS.items():
            with self.subTest(job=request_id):
                view = restored.views[request_id]
                kind = self.lane_kind[lane]
                self.assertEqual((view.lane, view.kind), (lane, kind))
                (text, icon), controls = before[request_id]
                self.assertEqual(text, PROMPT)
                self.assertEqual(icon, self.panels.KIND_ICON[kind])
                # The store keeps no prompt: the row names the catalog model instead.
                # Reload parameters needs the request, which is saved only as a hash.
                expected = [c for c in controls if c[0] != "scenario.reload_generation"]
                self.assertIn(("scenario.reload_generation", ""), controls)
                self.assertEqual(self.tools(view), ((name, icon), expected))
        # The Image result keeps its file tools, and its saved asset is reused.
        self.assertEqual(restored.views["still"].files, [files["still"]])
        controls = dict(before["still"][1])
        for operator in ("scenario.show_image", "scenario.use_as_reference"):
            self.assertIn(operator, controls)
        record, item = self.handoff.saved_reference(
            self.runtime.state.job_store, "still", files["still"]
        )
        self.assertEqual((record.intent.request_id, item.asset.asset_id), ("still", "asset-still"))
        # A Render Image still leads with its handoff to Render Video, as before.
        _, render = self.tools(restored.views["render"])
        self.assertEqual(render[0][0], "scenario.use_saved_first_frame")
        self.assertEqual(self.requests, [])

    def test_a_job_saved_without_its_lane_shows_the_kind_its_results_establish(self):
        # Saved by an earlier schema, or read from the cloud: no lane is known.
        path = self.save("still")
        self.save("mesh")
        restored = self.restart()
        self.assertTrue(self.settle(lambda: restored.views["still"].files))
        still, mesh = restored.views["still"], restored.views["mesh"]
        self.assertEqual((still.lane, still.kind, still.files), ("model", "image", [path]))
        self.assertEqual((mesh.lane, mesh.kind, mesh.files), ("model", "3d", []))
        (text, icon), controls = self.tools(still)
        self.assertEqual((text, icon), ("Fixture Image", "IMAGE_DATA"))
        operators = [operator for operator, _ in controls]
        self.assertIn("scenario.use_as_reference", operators)
        self.assertNotIn("scenario.reload_generation", operators)
        self.assertEqual(self.requests, [])

    def test_a_changed_saved_file_is_not_listed_after_a_restart(self):
        path = self.save("still", lane="image")
        Path(path).write_bytes(png(16, 8, b"\x00\x00\x00\xff"))
        restored = self.restart()
        record = self.runtime.state.job_store.get("still")
        # Settled once the preview-lane check found other bytes than the receipt's.
        self.assertTrue(self.settle(lambda: not restored._files.pending(record)))
        view = restored.views["still"]
        self.assertEqual((view.kind, view.files), ("image", []))
        operators = [operator for operator, _ in self.tools(view)[1]]
        self.assertNotIn("scenario.use_as_reference", operators)
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
