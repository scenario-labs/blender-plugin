# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped library MCP reads through installed SDK workers, without network."""

import json
import threading
import unittest
from unittest.mock import patch

import bpy
import httpx
import test_workflow_commands
from helpers import submodule


class AssetLibraryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workflow_commands.WorkflowCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime, self.tools = self.fixture.runtime, self.fixture.tools
        self.calls = []
        self.fail = False
        self.asset = {
            "id": "fixture-asset",
            "name": "Cup",
            "mimeType": "image/png",
            "metadata": {"type": "txt2img"},
            "tags": ["ceramic"],
            "url": "https://example.invalid/private-download",
            "ownerId": "private-owner",
            "content": "incomplete indexed text",
        }
        api = submodule("core.api.sdk_adapter")
        cls = api.SDKAdapter

        def factory(credentials, **options):
            options["transport"] = httpx.MockTransport(self.respond)
            return cls(credentials, **options)

        self.enterContext(patch.object(api, "SDKAdapter", side_effect=factory))

    def respond(self, request):
        self.assertIsNot(threading.current_thread(), threading.main_thread())
        self.calls.append(request)
        if self.fail:
            return httpx.Response(403, json={"message": "private rejection"})
        if request.url.path == "/v1/assets":
            response = {"assets": [self.asset]}
            if not request.url.params.get("paginationToken"):
                response["nextPaginationToken"] = "next-page"
        else:
            self.assertEqual(request.url.path, "/v1/search/assets")
            body = json.loads(request.content)
            response = {"hits": [self.asset], "offset": body["offset"], "estimatedTotalHits": 3}
        return httpx.Response(200, json=response)

    def finish(self, deferred):
        return self.fixture.finish(deferred)

    def test_list_returns_reference_metadata_without_urls_or_indexed_text(self):
        result = self.finish(self.tools.list_assets({}))
        self.assertEqual(result["assets"][0]["asset_id"], "fixture-asset")
        self.assertEqual(result["assets"][0]["mime_type"], "image/png")
        self.assertEqual(result["next_pagination_token"], "next-page")
        serialized = json.dumps(result)
        for private in ("private-download", "private-owner", "incomplete indexed text"):
            self.assertNotIn(private, serialized)
        self.assertFalse(self.fixture.store.records())
        self.assertIsNone(self.runtime.state.model_jobs)
        self.assertEqual(len(self.calls), 1)

    def test_public_collection_cursor_is_explicit_and_scope_is_preserved(self):
        self.fixture.prefs.project_id = "fixture-project"
        args = {"public": True, "page_size": 2, "collection_id": "fixture-collection"}
        first = self.finish(self.tools.list_assets(args))
        self.assertEqual(len(self.calls), 1)
        second = self.finish(
            self.tools.list_assets({**args, "pagination_token": first["next_pagination_token"]})
        )
        self.assertIsNone(second["next_pagination_token"])
        for request in self.calls:
            self.assertEqual(request.url.params["projectId"], "fixture-project")
            self.assertEqual(request.url.params["collectionId"], "fixture-collection")
            self.assertEqual(request.url.params["privacy"], "public")

    def test_search_continuation_keeps_body_parameters(self):
        first = self.finish(self.tools.search_assets({"query": "cup", "limit": 1}))
        self.assertEqual(first["next_offset"], 1)
        self.finish(
            self.tools.search_assets({"query": "cup", "limit": 1, "offset": first["next_offset"]})
        )
        self.assertEqual(
            json.loads(self.calls[-1].content),
            {"query": "cup", "limit": 1, "offset": 1, "public": False},
        )
        self.assertEqual(dict(self.calls[-1].url.params), {})
        self.assertFalse(self.fixture.store.records())

    def test_scope_change_rejects_late_delivery(self):
        deferred = self.tools.list_assets({})
        deferred.run()
        self.fixture.prefs.project_id = "different-project"
        with self.assertRaisesRegex(submodule("core.api.errors").ScenarioError, "context changed"):
            deferred.finish(None)
        self.assertEqual(len(self.calls), 1)

    def test_removed_scene_rejects_metadata_delivery(self):
        scene = bpy.context.scene
        deferred = self.tools.search_assets({"query": "cup"})
        deferred.run()
        replacement = bpy.data.scenes.new("Replacement library scene")
        bpy.context.window.scene = replacement
        bpy.data.scenes.remove(scene)
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            deferred.finish(None)
        self.assertFalse(self.fixture.store.records())

    def test_failed_read_drains_ownership_and_allows_explicit_retry(self):
        self.fail = True
        session = self.runtime.ensure_job_session()
        with self.assertRaises(submodule("core.api.sdk_adapter").AdapterError) as caught:
            self.finish(self.tools.list_assets({}))
        self.assertNotIn("private rejection", str(caught.exception))
        self.assertFalse(session._asset_reads)
        self.assertFalse(session._pending)
        self.fail = False
        self.assertEqual(len(self.finish(self.tools.list_assets({}))["assets"]), 1)
        self.assertEqual(len(self.calls), 2)

    def test_invalid_search_never_reaches_transport(self):
        with self.assertRaises(ValueError):
            self.finish(self.tools.search_assets({"query": "", "limit": 1}))
        self.assertFalse(self.calls)
        self.assertFalse(self.runtime.state.job_session._asset_reads)
