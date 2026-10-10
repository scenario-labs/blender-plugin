# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed local MCP organization tools over the application-owned JobSession.

A stateful MockTransport service implements the SDK 2.2.0 collection and tag
wire forms and answers only on worker threads. Nothing reaches the network,
spends credits, persists a job or changes Blender data.
"""

import json
import threading
import unittest
from unittest.mock import patch

import bpy
import httpx
import test_workflow_commands
from helpers import online_access, submodule

PRIVATE = "private-service-text"
PROJECTION = {"collection_id", "name", "asset_count", "model_count", "updated_at"}


def collection(identifier, name):
    return {
        "id": identifier,
        "name": name,
        "assetCount": 0,
        "itemCount": 0,
        "modelCount": 0,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
        "ownerId": "private-owner",
        "thumbnail": {"assetId": "x", "url": "https://cdn.example.invalid/private-thumb"},
    }


class Service:
    """Record every request; ``faults`` maps (method, path) to scripted behaviors.

    An int status refuses without applying, ``"apply-timeout"`` applies the
    change and then loses the response.
    """

    def __init__(self):
        self.assets = {
            identifier: {
                "id": identifier,
                "name": identifier.title(),
                "tags": [],
                "collectionIds": [],
                "url": "https://cdn.example.invalid/private-download?signature=secret",
                "ownerId": "private-owner",
            }
            for identifier in ("asset-a", "asset-b", "asset-c")
        }
        self.collections = {
            identifier: collection(identifier, name)
            for identifier, name in (("props", "Props"), ("sets", "Sets"), ("hero", "Hero"))
        }
        self.project = None
        self.requests = []
        self.faults = {}
        self.created = 0
        self.gate = None
        self.lock = threading.Lock()

    @property
    def writes(self):
        return [
            (method, path, body)
            for method, path, body in self.requests
            if method != "GET" and path != "/v1/assets/get-bulk"
        ]

    def fault(self, method, path, *behaviors):
        self.faults.setdefault((method, path), []).extend(behaviors)

    def __call__(self, request):
        if threading.current_thread() is threading.main_thread():
            raise AssertionError("Organization requests must run on job workers")
        if self.gate is not None:
            self.gate(request)
        body = json.loads(request.content) if request.content else None
        method, path = request.method, request.url.path
        with self.lock:
            self.requests.append((method, path, body))
            if request.url.params.get("projectId") != self.project:
                raise AssertionError("Request left the selected project scope")
            behaviors = self.faults.get((method, path))
            behavior = behaviors.pop(0) if behaviors else None
        if isinstance(behavior, int):
            return httpx.Response(behavior, json={"message": PRIVATE})
        response = self.route(method, path, body, request)
        if behavior == "apply-timeout":
            raise httpx.ReadTimeout(PRIVATE, request=request)
        return response

    def route(self, method, path, body, request):
        parts = path.removeprefix("/v1/").split("/")
        if parts == ["assets", "get-bulk"] and method == "POST":
            records = [self.assets[i] for i in body["assetIds"] if i in self.assets]
            return httpx.Response(200, json={"assets": json.loads(json.dumps(records))})
        if parts == ["collections"] and method == "GET":
            size = int(request.url.params.get("pageSize", 50))
            start = int(request.url.params.get("paginationToken", "0"))
            records = list(self.collections.values())
            page = {"collections": records[start : start + size]}
            if start + size < len(records):
                page["nextPaginationToken"] = str(start + size)
            return httpx.Response(200, json=page)
        if parts == ["collections"] and method == "POST":
            self.created += 1
            record = collection(f"created-{self.created}", body["name"])
            self.collections[record["id"]] = record
            return httpx.Response(200, json={"collection": record})
        if len(parts) == 2 and parts[0] == "collections" and method == "GET":
            return httpx.Response(200, json={"collection": self.collections[parts[1]]})
        if len(parts) == 3 and parts[0] == "collections" and parts[2] == "assets":
            for identifier in body["assetIds"]:
                members = self.assets[identifier]["collectionIds"]
                if method == "PUT" and parts[1] not in members:
                    members.append(parts[1])
                elif method == "DELETE" and parts[1] in members:
                    members.remove(parts[1])
            return httpx.Response(200, json={"collection": self.collections[parts[1]]})
        if len(parts) == 3 and parts[0] == "assets" and parts[2] == "tags":
            item = self.assets[parts[1]]
            if body["strict"] is not False:
                raise AssertionError("Tag changes must be non-strict")
            added = [tag for tag in body.get("add", []) if tag not in item["tags"]]
            deleted = [tag for tag in body.get("delete", []) if tag in item["tags"]]
            item["tags"] = [tag for tag in item["tags"] if tag not in deleted] + added
            return httpx.Response(200, json={"added": added, "deleted": deleted})
        raise AssertionError(f"Unexpected request {method} {path}")


def blender_state():
    data = bpy.data
    return tuple(
        len(items)
        for items in (data.objects, data.scenes, data.collections, data.images, data.materials)
    )


class AssetOrganizationToolTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workflow_commands.WorkflowCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime, self.tools = self.fixture.runtime, self.fixture.tools
        self.errors = submodule("core.api.errors")
        self.organization = submodule("core.jobs.organization")
        self.service = Service()
        api = submodule("core.api.sdk_adapter")
        cls = api.SDKAdapter

        def factory(credentials, **options):
            options["transport"] = httpx.MockTransport(self.service)
            return cls(credentials, **options)

        self.enterContext(patch.object(api, "SDKAdapter", side_effect=factory))

    def finish(self, deferred):
        return self.fixture.finish(deferred)

    def prepare(self, **arguments):
        return self.finish(self.tools.prepare_asset_organization(arguments))

    def ready(self, **arguments):
        review = self.prepare(**arguments)
        self.assertEqual(review["phase"], "READY", review["message"])
        self.assertIn("explicit approval", review["note"])
        return review

    def apply(self, review, **changes):
        arguments = {"context_id": review["context_id"], "review_id": review["review_id"]}
        return self.finish(self.tools.apply_asset_organization({**arguments, **changes}))

    def status(self, review, **changes):
        arguments = {"context_id": review["context_id"], "review_id": review["review_id"]}
        return self.tools.asset_organization_status({**arguments, **changes})

    def assert_public(self, value):
        serialized = json.dumps(value)
        for private in ("private", "signature", "cdn.example"):
            self.assertNotIn(private, serialized)

    def test_tools_are_registered_with_their_annotations(self):
        specs = {spec.name: spec for spec in self.tools.SPECS}
        expected = {
            "list_collections": {"readOnlyHint": True},
            "prepare_asset_organization": {"readOnlyHint": True},
            "apply_asset_organization": {"destructiveHint": True},
            "asset_organization_status": {"readOnlyHint": True},
        }
        for name, annotations in expected.items():
            self.assertEqual(specs[name].annotations, annotations, name)
            self.assertFalse(specs[name].offthread, name)
        names = set(submodule("blender.mcp_service").build_registry().names())
        self.assertLessEqual(set(expected), names)
        instructions = submodule("mcp.protocol").INSTRUCTIONS
        for name in ("prepare_asset_organization", "apply_asset_organization"):
            self.assertIn(name, instructions)

    def test_collection_pages_omit_thumbnails_and_owner_ids(self):
        first = self.finish(self.tools.list_collections({"page_size": 2}))
        self.assertEqual([row["collection_id"] for row in first["collections"]], ["props", "sets"])
        self.assertEqual(set(first), {"collections", "next_pagination_token"})
        for row in first["collections"]:
            self.assertEqual(set(row), PROJECTION)
        second = self.finish(
            self.tools.list_collections(
                {"page_size": 2, "pagination_token": first["next_pagination_token"]}
            )
        )
        self.assertEqual([row["collection_id"] for row in second["collections"]], ["hero"])
        self.assertIsNone(second["next_pagination_token"])
        self.assert_public([first, second])
        self.assertEqual(len(self.service.requests), 2)
        self.assertEqual(self.service.writes, [])
        self.assertFalse(self.fixture.store.records())
        self.assertIsNone(self.runtime.state.model_jobs)

    def test_invalid_arguments_send_nothing_and_leave_no_review(self):
        for arguments in ({"page_size": 0}, {"page_size": True}, {"pagination_token": ""}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.tools.list_collections(arguments)
        invalid = (
            {"asset_ids": ["asset-a"], "collection_id": "props"},
            {"operation": "rename", "asset_ids": ["asset-a"]},
            {"operation": "add_to_collection", "asset_ids": ["asset-a"], "collection": "props"},
            {"operation": "add_to_collection", "asset_ids": ["asset-a"]},
            {"operation": "add_to_collection", "asset_ids": "asset-a", "collection_id": "props"},
            {"operation": "add_to_collection", "asset_ids": [], "collection_id": "props"},
            {
                "operation": "add_to_collection",
                "asset_ids": [f"asset-{index}" for index in range(50)],
                "collection_id": "props",
            },
            {"operation": "update_tags", "asset_ids": ["asset-a", "asset-a"], "add_tags": ["x"]},
            {"operation": "update_tags", "asset_ids": ["asset-a"], "add_tags": ["a,b"]},
            {"operation": "update_tags", "asset_ids": ["asset-a"]},
            {
                "operation": "update_tags",
                "asset_ids": ["asset-a"],
                "add_tags": ["x"],
                "remove_tags": ["x"],
            },
            {"operation": "create_collection", "collection_name": " "},
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.tools.prepare_asset_organization(arguments)
        owner = self.runtime.state.job_session.asset_organization
        self.assertEqual(owner.reviews._reviews, {})
        self.assertEqual(self.service.requests, [])

    def test_add_then_remove_verify_with_one_request_each(self):
        self.service.assets["asset-a"]["collectionIds"].append("props")
        before = blender_state()
        arguments = {"asset_ids": ["asset-a", "asset-b"], "collection_id": "props"}
        review = self.ready(operation="add_to_collection", **arguments)
        self.assertEqual(review["collection_name"], "Props")
        self.assertIsNone(review["project_id"])
        self.assertEqual(review["request_count"], 1)
        self.assertEqual(
            [
                (row["asset_id"], row["in_collection"], row["change"]["membership"])
                for row in review["assets"]
            ],
            [("asset-a", True, None), ("asset-b", False, "add")],
        )
        self.assertIn("Blender Undo", review["notice"])
        self.assertEqual(self.service.writes, [])
        result = self.apply(review)
        self.assertEqual(result["phase"], "FINISHED")
        self.assertEqual(result["result"]["state"], "VERIFIED")
        self.assertEqual(result["result"]["requests_sent"], 1)
        self.assertEqual(
            [row["in_collection"] for row in result["result"]["outcomes"]], [True, True]
        )
        self.assertIn("confirmed every change", result["note"])
        review = self.ready(operation="remove_from_collection", **arguments)
        self.assertEqual(review["request_count"], 1)
        result = self.apply(review)
        self.assertEqual(result["result"]["state"], "VERIFIED")
        self.assertEqual(
            self.service.writes,
            [
                ("PUT", "/v1/collections/props/assets", {"assetIds": ["asset-b"]}),
                ("DELETE", "/v1/collections/props/assets", {"assetIds": ["asset-a", "asset-b"]}),
            ],
        )
        self.assertEqual(blender_state(), before)
        self.assertFalse(self.fixture.store.records())
        self.assert_public(result)
        # Both surfaces read the same session-owned review.
        owner = self.runtime.state.job_session.asset_organization
        shared = owner.status(review["review_id"])
        self.assertEqual(
            {**shared, "context_id": result["context_id"], "note": result["note"]}, result
        )

    def test_tag_changes_send_only_what_differs(self):
        self.service.assets["asset-a"]["tags"] = ["hero"]
        self.service.assets["asset-b"]["tags"] = ["old"]
        review = self.ready(
            operation="update_tags",
            asset_ids=["asset-a", "asset-b", "asset-c"],
            add_tags=[" hero ", "prop"],
            remove_tags=["old"],
        )
        self.assertEqual(review["add_tags"], ["hero", "prop"])
        self.assertEqual(review["request_count"], 3)
        result = self.apply(review)
        self.assertEqual(result["result"]["state"], "VERIFIED")
        self.assertEqual(
            self.service.writes,
            [
                ("PUT", "/v1/assets/asset-a/tags", {"add": ["prop"], "strict": False}),
                (
                    "PUT",
                    "/v1/assets/asset-b/tags",
                    {"add": ["hero", "prop"], "delete": ["old"], "strict": False},
                ),
                ("PUT", "/v1/assets/asset-c/tags", {"add": ["hero", "prop"], "strict": False}),
            ],
        )
        unchanged = self.prepare(
            operation="update_tags", asset_ids=["asset-a"], add_tags=["hero", "prop"]
        )
        self.assertEqual(unchanged["phase"], "UNCHANGED")
        self.assertIn("nothing will be sent", unchanged["note"])
        self.assertEqual(len(self.service.writes), 3)

    def test_create_then_add_and_existing_name_is_refused(self):
        review = self.ready(
            operation="create_collection", collection_name="Hero props", asset_ids=["asset-a"]
        )
        self.assertEqual(review["request_count"], 2)
        result = self.apply(review)
        self.assertEqual(result["result"]["state"], "VERIFIED")
        self.assertEqual(result["result"]["created_collection_id"], "created-1")
        self.assertEqual(result["result"]["create_outcome"], "VERIFIED")
        self.assertTrue(result["result"]["outcomes"][0]["in_collection"])
        self.assertEqual(
            [(method, path) for method, path, _ in self.service.writes],
            [("POST", "/v1/collections"), ("PUT", "/v1/collections/created-1/assets")],
        )
        # JSON null lists are omitted lists; the exact-name lookup still refuses.
        again = self.prepare(
            operation="create_collection", collection_name="Hero props", asset_ids=None
        )
        self.assertEqual(again["phase"], "REJECTED")
        self.assertEqual(again["existing_collection_ids"], ["created-1"])
        self.assertIn("add_to_collection", again["note"])
        self.assertEqual(len(self.service.writes), 2)

    def test_name_taken_before_apply_points_to_the_existing_collection(self):
        review = self.ready(
            operation="create_collection", collection_name="Rival set", asset_ids=["asset-a"]
        )
        # Another client creates the same exact name after the review was prepared.
        self.service.collections["rival"] = collection("rival", "Rival set")
        result = self.apply(review)
        self.assertEqual(result["phase"], "NOT_SENT")
        self.assertIsNone(result["result"])
        self.assertEqual(result["existing_collection_ids"], ["rival"])
        self.assertIn("Nothing was sent", result["note"])
        self.assertIn("prepare add_to_collection with its ID", result["note"])
        self.assertEqual(self.service.writes, [])

    def test_mismatched_context_and_reused_review_are_rejected(self):
        review = self.ready(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
        with self.assertRaisesRegex(self.errors.ScenarioError, "connection changed"):
            self.apply(review, context_id="another-context")
        with self.assertRaisesRegex(self.errors.ScenarioError, "connection changed"):
            self.status(review, context_id="another-context")
        for arguments in ({"context_id": review["context_id"]}, {"review_id": "x"}):
            with self.assertRaises(ValueError):
                self.tools.apply_asset_organization(arguments)
        with self.assertRaises(ValueError):
            self.status(review, action="apply")
        self.assertEqual(self.service.writes, [])
        self.assertEqual(self.apply(review)["result"]["state"], "VERIFIED")
        with self.assertRaises(self.organization.ReviewUnavailable):
            self.apply(review)
        self.assertEqual(len(self.service.writes), 1)

    def test_credential_or_project_change_invalidates_review_without_writing(self):
        prefs = self.fixture.prefs
        changes = (("project_id", "fixture-project"), ("api_key", "other-fixture-key"))
        for field, value in changes:
            with self.subTest(field=field):
                review = self.ready(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
                previous = self.runtime.state.job_session
                saved = getattr(prefs, field)
                setattr(prefs, field, value)
                self.addCleanup(setattr, prefs, field, saved)
                self.service.project = prefs.project_id or None
                with self.assertRaisesRegex(self.errors.ScenarioError, "connection changed"):
                    self.apply(review)
                with self.assertRaisesRegex(self.errors.ScenarioError, "connection changed"):
                    self.status(review)
                self.assertFalse(previous.active)
                current = self.runtime.state.job_session
                self.assertIsNot(current, previous)
                with self.assertRaises(self.organization.ReviewUnavailable):
                    current.asset_organization.status(review["review_id"])
                self.assertEqual(self.service.writes, [])

    def test_scene_switch_keeps_review_and_file_load_retires_it(self):
        review = self.ready(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
        scene = bpy.context.window.scene
        other = bpy.data.scenes.new("Other organization scene")
        try:
            bpy.context.window.scene = other
            bpy.context.view_layer.update()
            self.assertEqual(self.status(review)["phase"], "READY")
            self.assertEqual(self.apply(review)["result"]["state"], "VERIFIED")
        finally:
            bpy.context.window.scene = scene
            bpy.data.scenes.remove(other)
        review = self.ready(operation="update_tags", asset_ids=["asset-b"], add_tags=["x"])
        submodule("blender.job_session")._load_pre(None)
        with self.assertRaisesRegex(self.errors.ScenarioError, "connection changed"):
            self.apply(review)
        self.assertEqual(len(self.service.writes), 1)

    def test_session_retired_during_apply_reports_unknown_outcome(self):
        review = self.ready(
            operation="update_tags", asset_ids=["asset-a", "asset-b"], add_tags=["x"]
        )
        entered, release = threading.Event(), threading.Event()

        def hold_first_write(request):
            if request.method == "PUT":
                entered.set()
                if not release.wait(5):
                    raise AssertionError("Test did not release the write")

        self.service.gate = hold_first_write
        deferred = self.tools.apply_asset_organization(
            {"context_id": review["context_id"], "review_id": review["review_id"]}
        )
        self.assertTrue(entered.wait(5))
        submodule("blender.job_session")._load_pre(None)
        release.set()
        deferred.run()
        with self.assertRaisesRegex(self.errors.ScenarioError, "outcome is unknown"):
            deferred.finish(None)
        # The sent write keeps its effect; the guard refused the next one.
        self.assertEqual(len(self.service.writes), 1)
        self.assertEqual(self.service.assets["asset-b"]["tags"], [])

    def test_applied_then_timed_out_write_is_never_resent(self):
        review = self.ready(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
        self.service.fault("PUT", "/v1/assets/asset-a/tags", "apply-timeout")
        result = self.apply(review)
        self.assertEqual(result["result"]["state"], "VERIFIED")
        self.assertEqual(result["result"]["requests_sent"], 1)
        review = self.ready(operation="update_tags", asset_ids=["asset-b"], add_tags=["x"])
        self.service.fault("PUT", "/v1/assets/asset-b/tags", "apply-timeout")
        self.service.fault("POST", "/v1/assets/get-bulk", 503)
        result = self.apply(review)
        self.assertEqual(result["result"]["state"], "UNCONFIRMED")
        self.assertEqual(result["result"]["outcomes"][0]["state"], "UNCONFIRMED")
        self.assertIn("Never repeat unconfirmed work", result["note"])
        self.assert_public(result)
        # A fresh review reads the applied state instead of writing again.
        again = self.prepare(operation="update_tags", asset_ids=["asset-b"], add_tags=["x"])
        self.assertEqual(again["phase"], "UNCHANGED")
        self.assertEqual(len(self.service.writes), 2)

    def test_status_recovers_an_apply_whose_client_call_timed_out(self):
        review = self.ready(
            operation="add_to_collection", asset_ids=["asset-a"], collection_id="props"
        )
        # The client gave up: the deferred tool is never run or finished.
        self.tools.apply_asset_organization(
            {"context_id": review["context_id"], "review_id": review["review_id"]}
        )
        owner = self.runtime.state.job_session.asset_organization
        owner.task(review["review_id"]).result(5)
        status = self.status(review)
        self.assertEqual(status["phase"], "FINISHED")
        self.assertEqual(status["result"]["state"], "VERIFIED")
        with self.assertRaises(self.organization.ReviewUnavailable):
            self.apply(review)
        self.assertEqual(len(self.service.writes), 1)

    def test_online_access_off_sends_nothing(self):
        review = self.ready(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
        reads = len(self.service.requests)
        with online_access(False):
            self.runtime.sync_catalog_context()
            prepared = self.prepare(operation="update_tags", asset_ids=["asset-b"], add_tags=["x"])
            self.assertEqual(prepared["phase"], "REJECTED")
            self.assertIn("Online access is disabled", prepared["message"])
            result = self.apply(review)
            self.assertEqual(result["phase"], "NOT_SENT")
            self.assertIn("Nothing was sent", result["note"])
        self.assertEqual(len(self.service.requests), reads)

    def test_service_text_never_reaches_results(self):
        self.service.fault("POST", "/v1/assets/get-bulk", 500)
        failed = self.prepare(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
        self.assertEqual(failed["phase"], "REJECTED")
        self.assert_public(failed)
        review = self.ready(
            operation="update_tags", asset_ids=["asset-a", "asset-b"], add_tags=["x"]
        )
        self.service.fault("PUT", "/v1/assets/asset-a/tags", 403)
        result = self.apply(review)
        outcomes = result["result"]["outcomes"]
        self.assertEqual(
            [(row["state"], row["status"]) for row in outcomes],
            [("REJECTED", 403), ("VERIFIED", None)],
        )
        self.assertEqual(result["result"]["state"], "PARTIAL")
        self.assertIn("retry refused assets", result["note"])
        self.assert_public(result)
        self.service.fault("GET", "/v1/collections", 500)
        with self.assertRaises(submodule("core.api.sdk_adapter").AdapterError) as caught:
            self.finish(self.tools.list_collections({}))
        self.assertNotIn(PRIVATE, str(caught.exception))
        self.assertEqual(len(self.service.writes), 2)

    def test_discarded_review_cannot_apply(self):
        review = self.ready(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
        discarded = self.status(review, action="discard")
        self.assertEqual(discarded["phase"], "DISCARDED")
        self.assertIn("sends nothing more", discarded["note"])
        with self.assertRaises(self.organization.ReviewUnavailable):
            self.apply(review)
        self.assertEqual(self.service.writes, [])

    def test_discarding_an_applied_review_keeps_its_result(self):
        review = self.ready(operation="update_tags", asset_ids=["asset-a"], add_tags=["x"])
        self.assertEqual(self.apply(review)["result"]["state"], "VERIFIED")
        discarded = self.status(review, action="discard")
        self.assertEqual(discarded["phase"], "DISCARDED")
        self.assertEqual(discarded["result"]["state"], "VERIFIED")
        self.assertIn("after it was applied", discarded["note"])
        self.assertIn("report its result", discarded["note"])
        self.assertEqual(len(self.service.writes), 1)
