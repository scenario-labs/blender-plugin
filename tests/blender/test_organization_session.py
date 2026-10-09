# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed organization reviews: session ownership, delivery and retirement.

A stateful MockTransport fake service answers on worker threads. Nothing
reaches the network, spends credits or changes Blender data.
"""

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bpy
import httpx
import test_workflow_commands
from helpers import submodule

PRIVATE = "private-service-text"


class Service:
    """Collections, memberships and tags behind the SDK 2.2.0 wire forms."""

    def __init__(self):
        self.assets = {
            identifier: {
                "id": identifier,
                "name": identifier.title(),
                "tags": [],
                "collectionIds": [],
                "url": "https://cdn.example.invalid/private-download?signature=secret",
            }
            for identifier in ("asset-a", "asset-b")
        }
        self.collections = {
            "props": {
                "id": "props",
                "name": "Props",
                "assetCount": 0,
                "modelCount": 0,
                "updatedAt": "2026-01-01T00:00:00Z",
                "ownerId": "private-owner",
                "thumbnail": {"assetId": "x", "url": "https://cdn.example.invalid/private"},
            }
        }
        self.requests = []
        self.gate = None
        self.lock = threading.Lock()

    @property
    def writes(self):
        return [
            (method, path)
            for method, path, _ in self.requests
            if method != "GET" and path != "/v1/assets/get-bulk"
        ]

    def __call__(self, request):
        if threading.current_thread() is threading.main_thread():
            raise AssertionError("Organization requests must run on job workers")
        if self.gate is not None:
            self.gate(request)
        body = json.loads(request.content) if request.content else None
        method, path = request.method, request.url.path
        with self.lock:
            self.requests.append((method, path, body))
        parts = path.removeprefix("/v1/").split("/")
        if parts == ["assets", "get-bulk"]:
            records = [self.assets[i] for i in body["assetIds"] if i in self.assets]
            return httpx.Response(200, json={"assets": records})
        if parts == ["collections"] and method == "GET":
            return httpx.Response(200, json={"collections": list(self.collections.values())})
        if len(parts) == 2 and parts[0] == "collections":
            return httpx.Response(200, json={"collection": self.collections[parts[1]]})
        if len(parts) == 3 and parts[0] == "collections":
            for identifier in body["assetIds"]:
                members = self.assets[identifier]["collectionIds"]
                if method == "PUT" and parts[1] not in members:
                    members.append(parts[1])
            return httpx.Response(200, json={"collection": self.collections[parts[1]]})
        if len(parts) == 3 and parts[2] == "tags":
            tags = self.assets[parts[1]]["tags"]
            added = [tag for tag in body.get("add", []) if tag not in tags]
            tags.extend(added)
            return httpx.Response(200, json={"added": added, "deleted": []})
        return httpx.Response(500, json={"message": PRIVATE})


def blender_state():
    data = bpy.data
    return tuple(
        len(items)
        for items in (data.objects, data.scenes, data.collections, data.images, data.materials)
    )


class OrganizationSessionTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.job_session")
        self.organization = submodule("core.jobs.organization")
        api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        temp = tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        self.addCleanup(temp.cleanup)
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Organization fixture")
        bpy.context.window.scene = self.scene
        self.scope = storage.JobScope("https://fixture.invalid/v1", "fixture-account")
        self.store = storage.JobStore(Path(temp.name) / "jobs.sqlite3", self.scope)
        self.service = Service()
        self.online = True
        adapter = api.SDKAdapter(
            api.Credentials("key", "secret"),
            online=lambda: self.online,
            account_id=self.scope.account_id,
            base_url=self.scope.service,
            transport=httpx.MockTransport(self.service),
        )
        self.addCleanup(adapter.close)
        self.session = self.module.JobSession(adapter, self.store, workers=1)
        self.owner = self.session.asset_organization

    def tearDown(self):
        self.session.shutdown()
        if self.previous in tuple(bpy.data.scenes):
            bpy.context.window.scene = self.previous
        if self.scene in tuple(bpy.data.scenes):
            bpy.data.scenes.remove(self.scene)

    def settle(self, review_id):
        task = self.owner.task(review_id)
        if task is not None:
            try:
                task.result(5)
            except Exception:
                pass  # Delivery reports the owned outcome on the main thread.
        self.owner.poll()
        return self.owner.status(review_id)

    def ready(self, **arguments):
        arguments = arguments or {"asset_ids": ["asset-a", "asset-b"], "add_tags": ["hero"]}
        operation = arguments.pop("operation", "update_tags")
        review_id = self.owner.prepare(operation, **arguments)
        self.assertEqual(self.owner.status(review_id)["phase"], "PREPARING")
        status = self.settle(review_id)
        self.assertEqual(status["phase"], "READY", status["message"])
        return review_id

    def test_prepare_and_apply_verify_on_workers_without_changing_blender(self):
        before = blender_state()
        review_id = self.ready()
        status = self.owner.status(review_id)
        self.assertEqual(status["request_count"], 2)
        self.assertEqual(self.service.writes, [])
        self.assertEqual(self.owner.apply(review_id)["phase"], "APPLYING")
        status = self.settle(review_id)
        self.assertEqual(status["phase"], "FINISHED")
        self.assertEqual(status["result"]["state"], "VERIFIED")
        self.assertEqual(status["result"]["requests_sent"], 2)
        self.assertEqual(len(self.service.writes), 2)
        self.assertEqual(blender_state(), before)
        self.assertFalse(self.store.records())
        self.assertNotIn("private", json.dumps(status))
        with self.assertRaises(self.organization.ReviewUnavailable):
            self.owner.apply(review_id)
        self.assertEqual(len(self.service.writes), 2)

    def test_other_connection_and_foreign_completions_are_refused(self):
        storage = submodule("core.jobs.store")
        other = storage.JobScope(self.scope.service, self.scope.account_id, "other-project")
        request = self.organization.build_request(
            other, "update_tags", asset_ids=["asset-a"], add_tags=["hero"]
        )
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.organization_snapshot(request)
        self.assertEqual(self.service.requests, [])
        task = self.session.collection_page(page_size=10)
        task.result(5)
        completion = self.session.drain(task=task)[0]
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Resolved a scene"))
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver_asset_library(completion)
        page = self.session.deliver_asset_organization(completion)
        self.assertEqual(page["collections"][0]["id"], "props")
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver_asset_organization(completion)

    def test_collection_pages_omit_thumbnails_and_owner_ids(self):
        task = self.owner.collections(page_size=10)
        task.result(5)
        page = self.owner.take_collections(task)
        self.assertEqual(page["collections"][0]["collection_id"], "props")
        self.assertIsNone(page["next_pagination_token"])
        self.assertNotIn("private", json.dumps(page))

    def test_undo_and_scene_switch_keep_reviews(self):
        review_id = self.ready()
        self.module._history_pre(None)
        other = bpy.data.scenes.new("Other organization scene")
        try:
            bpy.context.window.scene = other
            bpy.context.view_layer.update()
            self.assertEqual(self.owner.status(review_id)["phase"], "READY")
            self.owner.apply(review_id)
            status = self.settle(review_id)
        finally:
            bpy.context.window.scene = self.scene
            bpy.data.scenes.remove(other)
        self.assertEqual(status["result"]["state"], "VERIFIED")

    def test_file_load_retires_reviews_and_stops_later_writes(self):
        review_id = self.ready()
        entered, release = threading.Event(), threading.Event()

        def hold_first_write(request):
            if request.method == "PUT":
                entered.set()
                self.assertTrue(release.wait(5), "Test did not release the write")

        self.service.gate = hold_first_write
        self.owner.apply(review_id)
        task = self.owner.task(review_id)
        self.assertTrue(entered.wait(5))
        self.module._load_pre(None)
        release.set()
        result = task.result(5)
        # The sent write keeps its effect; the guard refused the next one.
        self.assertEqual(len(self.service.writes), 1)
        self.assertEqual([outcome.state.value for outcome in result.outcomes][1], "NOT_SENT")
        with self.assertRaises(self.organization.ReviewUnavailable):
            self.owner.status(review_id)
        completion = self.session.drain(task=task)[0]
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver_asset_organization(completion)
        with self.assertRaises(self.module.OriginUnavailable):
            self.owner.prepare("update_tags", asset_ids=["asset-a"], add_tags=["x"])

    def test_online_access_off_reports_nothing_sent(self):
        review_id = self.ready()
        self.online = False
        self.owner.apply(review_id)
        status = self.settle(review_id)
        self.assertEqual(status["phase"], "NOT_SENT")
        self.assertIn("Online access is disabled", status["message"])
        self.assertEqual(self.service.writes, [])

    def test_discarded_review_cannot_apply(self):
        review_id = self.ready()
        self.assertEqual(self.owner.discard(review_id)["phase"], "DISCARDED")
        with self.assertRaises(self.organization.ReviewUnavailable):
            self.owner.apply(review_id)
        self.assertEqual(self.service.writes, [])

    def test_refused_admission_keeps_the_review_ready(self):
        review_id = self.ready()
        busy = self.module.SessionBusy("Drain completed job outcomes first")
        with (
            patch.object(self.session, "_check_capacity", side_effect=busy),
            self.assertRaises(self.module.SessionBusy),
        ):
            self.owner.apply(review_id)
        self.assertEqual(self.owner.status(review_id)["phase"], "READY")
        self.assertEqual(self.service.writes, [])
        self.owner.apply(review_id)
        self.assertEqual(self.settle(review_id)["result"]["state"], "VERIFIED")

    def test_existing_name_is_refused_with_its_id(self):
        review_id = self.owner.prepare("create_collection", collection_name="Props")
        status = self.settle(review_id)
        self.assertEqual(status["phase"], "REJECTED")
        self.assertEqual(status["existing_collection_ids"], ["props"])
        self.assertEqual(self.service.writes, [])

    def test_worker_threads_cannot_use_the_organization_owner(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                self.owner.prepare, "update_tags", asset_ids=["asset-a"], add_tags=["x"]
            )
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                future.result(5)
        self.assertEqual(self.service.requests, [])


class OrganizationRuntimeTests(unittest.TestCase):
    """The application pump owns progress; a project change retires reviews."""

    def setUp(self):
        self.fixture = test_workflow_commands.WorkflowCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.runtime
        self.service = Service()
        api = submodule("core.api.sdk_adapter")
        cls = api.SDKAdapter

        def factory(credentials, **options):
            options["transport"] = httpx.MockTransport(self.service)
            return cls(credentials, **options)

        self.enterContext(patch.object(api, "SDKAdapter", side_effect=factory))

    def test_pump_settles_reviews_and_project_change_retires_them(self):
        session = self.runtime.ensure_job_session()
        owner = session.asset_organization
        review_id = owner.prepare("add_to_collection", asset_ids=["asset-a"], collection_id="props")
        owner.task(review_id).result(5)
        # Application-owned maintenance progresses reviews without a panel.
        self.runtime.sync_catalog_context()
        self.assertEqual(owner.status(review_id)["phase"], "READY")
        self.fixture.prefs.project_id = "fixture-project"
        self.runtime.sync_catalog_context()
        self.assertFalse(session.active)
        organization = submodule("core.jobs.organization")
        with self.assertRaises(organization.ReviewUnavailable):
            owner.status(review_id)
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            owner.apply(review_id)
        replacement = self.runtime.ensure_job_session()
        self.assertIsNot(replacement, session)
        with self.assertRaises(organization.ReviewUnavailable):
            replacement.asset_organization.status(review_id)
        self.assertEqual(self.service.writes, [])
