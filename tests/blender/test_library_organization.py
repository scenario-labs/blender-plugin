# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed native Library organization over the session's shared reviews.

The stateful SDK 2.2.0 wire-form fake from the MCP organization tests also
serves asset pages here, answering only on worker threads. Nothing reaches the
network, spends credits, persists a job or changes Blender data.
"""

import gc
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import httpx
import test_asset_organization
import test_workflow_commands
from helpers import online_access, submodule

PRIVATE = test_asset_organization.PRIVATE
PROJECTION = test_asset_organization.PROJECTION
ICONS = frozenset(bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items.keys())


class LibraryService(test_asset_organization.Service):
    """Adds explicit asset pages, filtered by collection, to the organization fake."""

    def route(self, method, path, body, request):
        if path == "/v1/assets" and method == "GET":
            wanted = request.url.params.get("collectionId")
            rows = [
                {**json.loads(json.dumps(item)), "mimeType": "image/png"}
                for item in self.assets.values()
                if wanted is None or wanted in item["collectionIds"]
            ]
            return httpx.Response(200, json={"assets": rows})
        return super().route(method, path, body, request)


class Layout:
    """Record labels, properties and operator buttons with their enabled state."""

    def __init__(self, log=None, parent=None):
        self.log = [] if log is None else log
        self.parent = parent
        self.enabled = True

    def active(self):
        return self.enabled and (self.parent is None or self.parent.active())

    def box(self, *args, **kwargs):
        return Layout(self.log, self)

    row = column = split = box

    def separator(self, *args, **kwargs):
        pass

    def label(self, text="", icon="NONE", **kwargs):
        self.log.append(("label", text, icon, self))

    def prop(self, data, name, **kwargs):
        self.log.append(("prop", name, kwargs.get("text"), self))

    def operator(self, idname, text="", icon="NONE", **kwargs):
        properties = SimpleNamespace()
        self.log.append(("operator", idname, text, self, properties))
        return properties

    def labels(self):
        return [(entry[1], entry[2]) for entry in self.log if entry[0] == "label"]

    def texts(self):
        return [text for text, _ in self.labels()]

    def buttons(self, idname):
        return [
            (entry[2], entry[3].active(), entry[4])
            for entry in self.log
            if entry[0] == "operator" and entry[1] == idname
        ]


def blender_state():
    data = bpy.data
    return tuple(
        len(items)
        for items in (data.objects, data.scenes, data.collections, data.images, data.materials)
    )


class LibraryOrganizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workflow_commands.WorkflowCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.runtime
        self.module = submodule("blender.library_view")
        self.organizing = submodule("core.ui.library_organization")
        self.service = LibraryService()
        self.service.assets["asset-a"]["tags"] = ["hero"]
        self.service.assets["asset-a"]["collectionIds"] = ["props"]
        api = submodule("core.api.sdk_adapter")
        cls = api.SDKAdapter

        def factory(credentials, **options):
            options["transport"] = httpx.MockTransport(self.service)
            return cls(credentials, **options)

        self.enterContext(patch.object(api, "SDKAdapter", side_effect=factory))
        self.view = bpy.context.window_manager.scenario_library_view
        for key in ("target", "query", "public", "collection"):
            self.addCleanup(setattr, self.view, key, getattr(self.view, key))
        self.view.query, self.view.public, self.view.collection = "", False, ""
        studio = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, studio, "page", studio.page)
        studio.page = "LIBRARY"
        self.owner = self.module.controls(create=True)
        self.session = self.owner.session

    # Synchronization: wait for queued worker tasks, then run the real pump once.

    def settle(self):
        tasks = [self.owner.task, self.owner.collections_task]
        tasks += list(self.session.asset_organization._tasks)
        for task in tasks:
            if task is None:
                continue
            try:
                task.result(timeout=10)
            except Exception:
                # The pump records failures; each test checks that outcome.
                pass
        self.runtime.sync_catalog_context()

    def refresh(self):
        self.assertEqual(bpy.ops.scenario.library_page(direction="REFRESH"), {"FINISHED"})
        self.settle()
        self.assertFalse(self.owner.error, self.owner.error)

    def collections(self):
        self.assertEqual(bpy.ops.scenario.library_collections(direction="LOAD"), {"FINISHED"})
        self.settle()
        self.assertFalse(self.owner.collections_error, self.owner.collections_error)

    def row(self, asset_id):
        return next(row for row in self.owner.assets if row["asset_id"] == asset_id)

    def dialog(self, asset_id, **choices):
        """Invoke the registered dialog's methods on an operator stand-in."""
        operator = SimpleNamespace(
            asset_id=asset_id,
            menu_id="",
            action="ADD",
            collection_id="",
            collection_name="",
            tags="",
            report=MagicMock(),
            layout=Layout(),
        )
        manager = SimpleNamespace(invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"}))
        context = SimpleNamespace(scene=bpy.context.scene, window_manager=manager)
        cls = self.module.SCENARIO_OT_library_organize
        result = cls.invoke(operator, context, None)
        for key, value in choices.items():
            setattr(operator, key, value)
        return cls, operator, context, result

    def organize(self, asset_id, **choices):
        cls, operator, context, result = self.dialog(asset_id, **choices)
        self.assertEqual(result, {"RUNNING_MODAL"}, operator.report.call_args_list)
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.assertEqual(self.owner.review["phase"], "PREPARING")
        self.settle()
        return self.owner.review

    def apply(self):
        review_id = self.owner.review_id
        self.assertEqual(
            bpy.ops.scenario.library_organization_apply(review_id=review_id), {"FINISHED"}
        )
        self.assertEqual(self.owner.review["phase"], "APPLYING")
        self.settle()
        return self.owner.review

    def draw(self):
        layout = Layout()
        self.module.draw(layout, bpy.context)
        for _, icon in layout.labels():
            self.assertIn(icon, ICONS)
        return layout

    def assert_public(self, texts):
        serialized = json.dumps(texts)
        for private in (PRIVATE, "signature", "cdn.example", "private-owner"):
            self.assertNotIn(private, serialized)

    def test_operators_register_and_the_collection_enum_reads_operator_properties(self):
        for name in (
            "library_collections",
            "library_collection_filter",
            "library_organize",
            "library_organization_apply",
            "library_organization_discard",
        ):
            self.assertTrue(hasattr(bpy.types, "SCENARIO_OT_" + name), name)
        module, test = self.module, self

        class SCENARIO_OT_library_organize_probe(bpy.types.Operator):
            bl_idname = "scenario.library_organize_probe"
            bl_label = "Library organize enum regression probe"
            __annotations__ = module.SCENARIO_OT_library_organize.__annotations__.copy()

            def execute(self, context):
                self._menu = module.OrganizeMenu([("props", "Props", ""), ("sets", "Sets", "")])
                self.menu_id = "organize-probe"
                module._organize_menus[self.menu_id] = self._menu
                self.collection_id = "props"
                test.assertEqual(self.properties.collection_id, "props")
                self.properties.collection_id = "sets"
                test.assertEqual(self.collection_id, "sets")
                test.assertIs(module._collections(self.properties, context), self._menu.items)
                self.menu_id = "unknown-menu"
                test.assertEqual(
                    module._collections(self.properties, context), module._NO_COLLECTIONS
                )
                return {"FINISHED"}

        bpy.utils.register_class(SCENARIO_OT_library_organize_probe)
        try:
            self.assertEqual(bpy.ops.scenario.library_organize_probe(), {"FINISHED"})
        finally:
            bpy.utils.unregister_class(SCENARIO_OT_library_organize_probe)
        gc.collect()
        self.assertNotIn("organize-probe", module._organize_menus)
        properties = bpy.ops.scenario.library_organize.get_rna_type().properties
        for name in ("asset_id", "menu_id", "action", "collection_id", "collection_name", "tags"):
            self.assertTrue(properties[name].is_skip_save, name)

    def test_collections_load_more_and_browse_set_the_filter_in_execute(self):
        with patch.object(self.module, "COLLECTION_PAGE", 2):
            self.collections()
            self.assertEqual(
                [row["collection_id"] for row in self.owner.collections], ["props", "sets"]
            )
            for row in self.owner.collections:
                self.assertEqual(set(row), PROJECTION)
            self.assertTrue(self.owner.more_collections())
            self.assertEqual(bpy.ops.scenario.library_collections(direction="MORE"), {"FINISHED"})
            self.settle()
        self.assertEqual(
            [row["collection_id"] for row in self.owner.collections], ["props", "sets", "hero"]
        )
        self.assertFalse(self.owner.more_collections())
        self.assertEqual(bpy.ops.scenario.library_collections(direction="MORE"), {"CANCELLED"})
        self.assertEqual(len(self.service.requests), 2)
        self.view.query, self.view.public = "cup", True
        self.assertEqual(
            bpy.ops.scenario.library_collection_filter(collection_id="unknown"), {"CANCELLED"}
        )
        self.assertEqual((self.view.query, self.view.public), ("cup", True))
        self.assertEqual(
            bpy.ops.scenario.library_collection_filter(collection_id="props"), {"FINISHED"}
        )
        self.assertEqual(
            (self.view.query, self.view.public, self.view.collection), ("", False, "props")
        )
        self.settle()
        self.assertEqual(self.owner.filters, ("", False, "props"))
        self.assertEqual([row["asset_id"] for row in self.owner.assets], ["asset-a"])
        page = self.service.requests[-1]
        self.assertEqual(page[:2], ("GET", "/v1/assets"))
        self.assertEqual(self.service.writes, [])
        layout = self.draw()
        self.assertIn(("Props (0)", "CHECKMARK"), layout.labels())
        self.assertEqual(len(layout.buttons("scenario.library_collection_filter")), 3)

    def test_repeated_collection_cursor_is_not_followed(self):
        with patch.object(self.module, "COLLECTION_PAGE", 2):
            self.collections()
        loaded = list(self.owner.collections)
        self.assertEqual(self.owner.collections_next, "2")
        self.assertEqual(bpy.ops.scenario.library_collections(direction="MORE"), {"FINISHED"})
        # The page read with cursor "2" names the same cursor again.
        repeated = {"collections": [], "next_pagination_token": "2"}
        with patch.object(
            self.session.asset_organization, "take_collections", return_value=repeated
        ):
            self.settle()
        self.assertIn("repeated a collection page", self.owner.collections_error)
        self.assertEqual(self.owner.collections, loaded)

    def test_draw_is_read_only_and_shows_tags_memberships_and_the_card(self):
        self.collections()
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags="prop")
        session = self.session

        def state():
            view = tuple(
                getattr(self.view, key) for key in ("target", "query", "public", "collection")
            )
            return (
                view,
                len(self.service.requests),
                json.dumps(self.owner.review, sort_keys=True),
                json.dumps(self.owner.assets, sort_keys=True),
                len(session._pending),
                blender_state(),
            )

        before = state()
        refuse = AssertionError("draw started work")
        with (
            patch.object(session, "asset_library", side_effect=refuse),
            patch.object(session.asset_organization, "prepare", side_effect=refuse),
            patch.object(session.asset_organization, "apply", side_effect=refuse),
            patch.object(session.asset_organization, "discard", side_effect=refuse),
            patch.object(session.asset_organization, "collections", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_session", side_effect=refuse),
        ):
            layout = self.draw()
            submodule("blender.studio").draw_view(MagicMock(), bpy.context, width=400)
        self.assertEqual(state(), before)
        texts = layout.texts()
        self.assertIn("Tags: hero", texts)
        self.assertIn("In 1 collection: Props", texts)
        self.assertIn("No tags", texts)
        self.assertIn("In no collections", texts)
        self.assertIn("Organization review", texts)
        self.assertIn("Asset: Asset-B", texts)
        self.assertIn("Change: add prop", texts)
        self.assertIn("Apply sends 1 request once, with no retry", texts)
        labels = [text for text, _, _ in layout.buttons("scenario.library_organization_apply")]
        self.assertEqual(labels, ["Apply"])
        self.assert_public(texts)

    def test_long_labels_wrap_to_the_narrow_card_width(self):
        self.service.collections["props"]["name"] = "Collection " + "n" * 190
        self.service.assets["asset-b"]["name"] = "Asset " + "a" * 190
        self.collections()
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags="t" * 200 + ", " + "雪" * 120)
        self.assertEqual(self.owner.review["phase"], "READY", self.owner.review["message"])
        lines = self.organizing.review_lines(self.owner.review, names=self.owner.collection_names())
        texts = self.draw().texts()
        for text, icon in lines:
            self.assertLessEqual(len(text), self.organizing.WIDTH, text)
            self.assertIn(text, texts)
            self.assertIn(icon, ICONS)
        rows = [text for text in texts if text.startswith(("Tags:", "In 1 collection"))]
        self.assertTrue(rows)
        self.assertTrue(all(len(text) <= self.organizing.WIDTH for text in rows), rows)
        self.assertIn("Asset: Asset aaaa", " ".join(texts))

    def test_public_and_busy_pages_disable_organize(self):
        self.view.public = True
        self.refresh()
        self.assertIn("Public assets", self.owner.organize_block())
        layout = self.draw()
        self.assertIn("Organize is unavailable for Public assets", layout.texts())
        buttons = layout.buttons("scenario.library_organize")
        self.assertEqual(len(buttons), 3)
        self.assertFalse(any(active for _, active, _ in buttons))
        _, operator, _, result = self.dialog("asset-a")
        self.assertEqual(result, {"CANCELLED"})
        self.assertIn("Public assets", operator.report.call_args.args[1])
        self.view.public = False
        self.refresh()
        self.assertEqual(self.owner.organize_block(), "")
        self.assertEqual(bpy.ops.scenario.library_page(direction="REFRESH"), {"FINISHED"})
        self.assertIn("Library request", self.owner.organize_block())
        self.assertFalse(
            any(active for _, active, _ in self.draw().buttons("scenario.library_organize"))
        )
        self.settle()
        self.assertIsNone(self.owner.review)
        self.assertEqual(self.service.writes, [])

    def test_dialog_shows_asset_and_connection_and_cancel_changes_nothing(self):
        self.collections()
        self.refresh()
        reads = len(self.service.requests)
        cls, operator, context, result = self.dialog("asset-a")
        self.assertEqual(result, {"RUNNING_MODAL"})
        self.assertEqual(operator.collection_id, "props")
        cls.draw(operator, context)
        texts = operator.layout.texts()
        self.assertEqual(texts[:2], ["Asset: Asset-A", "Project: API key default scope"])
        self.assertIn("OK reads the current state for review; nothing is sent yet", texts)
        self.assertIn("Blender Undo", " ".join(texts))
        operator.layout, operator.action, operator.tags = Layout(), "ADD_TAGS", "bad\ttag"
        cls.draw(operator, context)
        problems = [text for text, icon in operator.layout.labels() if icon == "ERROR"]
        self.assertTrue(problems and "control" in problems[0], problems)
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        # Cancel is never executing: nothing was prepared or sent.
        self.assertIsNone(self.owner.review)
        self.assertEqual(self.session.asset_organization.reviews._reviews, {})
        self.assertEqual(len(self.service.requests), reads)
        self.assertEqual(bpy.ops.scenario.library_organize(asset_id="asset-a"), {"CANCELLED"})
        self.assertEqual(self.session.asset_organization.reviews._reviews, {})

    def test_add_to_collection_applies_once_and_updates_rows(self):
        before = blender_state()
        self.collections()
        self.refresh()
        cls, operator, context, _ = self.dialog("asset-b", action="ADD")
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.assertIn(
            "Reading the current state; nothing has been sent", " ".join(self.draw().texts())
        )
        # Apply is gated on READY: a preparing review cannot be applied.
        review_id = self.owner.review_id
        self.assertEqual(
            bpy.ops.scenario.library_organization_apply(review_id=review_id), {"CANCELLED"}
        )
        self.settle()
        review = self.owner.review
        self.assertEqual(review["phase"], "READY", review["message"])
        self.assertEqual(review["request_count"], 1)
        self.assertEqual(self.service.writes, [])
        self.assertEqual(
            bpy.ops.scenario.library_organization_apply(review_id="another-review"), {"CANCELLED"}
        )
        result = self.apply()
        self.assertEqual(result["phase"], "FINISHED")
        self.assertEqual(result["result"]["state"], "VERIFIED")
        self.assertEqual(
            bpy.ops.scenario.library_organization_apply(review_id=review_id), {"CANCELLED"}
        )
        self.assertEqual(
            self.service.writes,
            [("PUT", "/v1/collections/props/assets", {"assetIds": ["asset-b"]})],
        )
        self.assertEqual(self.row("asset-b")["collection_ids"], ["props"])
        texts = self.draw().texts()
        self.assertIn("Result: Verified by reading back", texts)
        self.assertEqual(texts.count("In 1 collection: Props"), 2)
        self.assertEqual(blender_state(), before)
        self.assertFalse(self.fixture.store.records())
        self.assertEqual(
            bpy.ops.scenario.library_organization_discard(review_id=review_id), {"FINISHED"}
        )
        self.assertIsNone(self.owner.review)
        self.assertEqual(len(self.service.writes), 1)

    def test_tag_changes_keep_unicode_text_and_update_rows(self):
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags=" héros , 雪 ")
        self.assertEqual(self.owner.review["add_tags"], ["héros", "雪"])
        self.assertEqual(self.apply()["result"]["state"], "VERIFIED")
        self.assertEqual(self.row("asset-b")["tags"], ["héros", "雪"])
        self.assertIn("Tags: héros, 雪", self.draw().texts())
        self.organize("asset-b", action="REMOVE_TAGS", tags="雪")
        self.assertEqual(self.apply()["result"]["state"], "VERIFIED")
        self.assertEqual(self.row("asset-b")["tags"], ["héros"])
        self.assertEqual(
            self.service.writes,
            [
                ("PUT", "/v1/assets/asset-b/tags", {"add": ["héros", "雪"], "strict": False}),
                ("PUT", "/v1/assets/asset-b/tags", {"delete": ["雪"], "strict": False}),
            ],
        )

    def test_removal_from_the_browsed_collection_marks_the_row_for_refresh(self):
        self.collections()
        self.assertEqual(
            bpy.ops.scenario.library_collection_filter(collection_id="props"), {"FINISHED"}
        )
        self.settle()
        _, operator, _, _ = self.dialog("asset-a", action="REMOVE")
        self.assertEqual(operator.collection_id, "props")
        self.organize("asset-a", action="REMOVE")
        self.assertEqual(self.apply()["result"]["state"], "VERIFIED")
        # The row stays until an explicit refresh and says why.
        self.assertEqual([row["asset_id"] for row in self.owner.assets], ["asset-a"])
        self.assertIn("asset-a", self.owner.stale)
        self.assertIn("No longer in this collection; refresh", self.draw().texts())
        self.refresh()
        self.assertEqual(self.owner.assets, [])
        self.assertFalse(self.owner.stale)

    def test_new_collection_is_created_once_and_names_rows(self):
        self.collections()
        self.refresh()
        review = self.organize("asset-b", action="CREATE", collection_name=" Hero props ")
        self.assertEqual(review["phase"], "READY", review["message"])
        self.assertEqual(review["request_count"], 2)
        result = self.apply()
        self.assertEqual(result["result"]["state"], "VERIFIED")
        self.assertEqual(self.owner.collections[-1]["collection_id"], "created-1")
        self.assertEqual(self.owner.collections[-1]["name"], "Hero props")
        self.assertIn("In 1 collection: Hero props", self.draw().texts())
        review = self.organize("asset-c", action="CREATE", collection_name="Hero props")
        self.assertEqual(review["phase"], "REJECTED")
        texts = self.draw().texts()
        self.assertIn("Existing: Hero props", texts)
        self.assertEqual(
            [text for text, _, _ in self.draw().buttons("scenario.library_organization_discard")],
            ["Dismiss"],
        )
        self.assertEqual(
            [(method, path) for method, path, _ in self.service.writes],
            [("POST", "/v1/collections"), ("PUT", "/v1/collections/created-1/assets")],
        )

    def test_closing_and_reopening_studio_during_apply_keeps_the_card(self):
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags="prop")
        entered, release = threading.Event(), threading.Event()

        def hold(request):
            if request.method == "PUT":
                entered.set()
                if not release.wait(5):
                    raise AssertionError("Test did not release the write")

        self.service.gate = hold
        studio = submodule("blender.studio")
        review_id = self.owner.review_id
        self.assertEqual(
            bpy.ops.scenario.library_organization_apply(review_id=review_id), {"FINISHED"}
        )
        self.assertTrue(entered.wait(5))
        layout = MagicMock()
        studio.draw_view(layout, bpy.context, width=960)
        drawn = " ".join(str(call.kwargs.get("text", "")) for call in layout.mock_calls)
        self.assertIn("Applying once", drawn)
        # Closing the popup owns nothing: the review keeps applying.
        self.assertIn("organization change to finish", self.owner.organize_block())
        release.set()
        self.settle()
        self.assertIs(self.runtime.state.library_view, self.owner)
        layout = MagicMock()
        studio.draw_view(layout, bpy.context, width=960)
        drawn = " ".join(str(call.kwargs.get("text", "")) for call in layout.mock_calls)
        self.assertIn("Result: Verified by reading back", drawn)
        self.assertEqual(len(self.service.writes), 1)

    def test_credential_project_or_file_change_clears_the_view_and_reviews(self):
        prefs = self.fixture.prefs
        changes = (
            ("project_id", "fixture-project"),
            ("api_key", "other-fixture-key"),
            (None, None),
        )
        for field, value in changes:
            with self.subTest(field=field or "file load"):
                self.owner = self.module.controls(create=True)
                self.session = self.owner.session
                self.service.project = prefs.project_id or None
                self.refresh()
                self.organize("asset-b", action="ADD_TAGS", tags="x")
                review_id = self.owner.review_id
                previous = self.session
                if field is None:
                    submodule("blender.job_session")._load_pre(None)
                else:
                    saved = getattr(prefs, field)
                    setattr(prefs, field, value)
                    self.addCleanup(setattr, prefs, field, saved)
                self.service.project = prefs.project_id or None
                self.runtime.sync_catalog_context()
                self.assertFalse(previous.active)
                self.assertIsNone(self.runtime.state.library_view)
                self.assertIsNone(self.module.controls())
                self.assertEqual(previous.asset_organization.reviews._reviews, {})
                self.assertEqual(
                    bpy.ops.scenario.library_organization_apply(review_id=review_id),
                    {"CANCELLED"},
                )
                self.assertIn("Refresh to load assets", " ".join(self.draw().texts()))
                self.assertEqual(self.service.writes, [])

    def test_sanitized_refusals_are_shown(self):
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags="x")
        self.service.fault("PUT", "/v1/assets/asset-b/tags", 403)
        result = self.apply()
        self.assertEqual(result["result"]["state"], "REJECTED")
        texts = self.draw().texts()
        self.assertIn("Result: Refused", texts)
        self.assertIn("Refused (HTTP 403)", texts)
        self.assert_public(texts)
        self.service.fault("GET", "/v1/collections", 500)
        self.assertEqual(bpy.ops.scenario.library_collections(direction="LOAD"), {"FINISHED"})
        self.settle()
        self.assertTrue(self.owner.collections_error)
        self.assert_public([self.owner.collections_error, *self.draw().texts()])
        self.assertEqual(len(self.service.writes), 1)

    def test_online_access_off_sends_nothing(self):
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags="x")
        requests = len(self.service.requests)
        with online_access(False):
            self.runtime.sync_catalog_context()
            with self.assertRaisesRegex(ValueError, "Online Access"):
                self.owner.organize("asset-a", "ADD_TAGS", tags="y")
            self.assertEqual(bpy.ops.scenario.library_collections(direction="LOAD"), {"FINISHED"})
            self.settle()
            self.assertIn("Online access is disabled", self.owner.collections_error)
            result = self.apply()
            self.assertEqual(result["phase"], "NOT_SENT")
            self.assertIn("Nothing was sent", " ".join(self.draw().texts()))
        self.assertEqual(len(self.service.requests), requests)

    def test_expired_review_cannot_apply_and_can_be_dismissed(self):
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags="x")
        reviews = self.session.asset_organization.reviews
        clock = reviews._clock
        self.enterContext(patch.object(reviews, "_clock", lambda: clock() + 601))
        self.settle()
        self.assertEqual(self.owner.review["phase"], "EXPIRED")
        review_id = self.owner.review_id
        self.assertEqual(
            bpy.ops.scenario.library_organization_apply(review_id=review_id), {"CANCELLED"}
        )
        self.assertIn("expired", " ".join(self.draw().texts()))
        self.assertEqual(
            bpy.ops.scenario.library_organization_discard(review_id=review_id), {"FINISHED"}
        )
        self.assertIsNone(self.owner.review)
        self.assertEqual(self.service.writes, [])

    def test_reviews_full_of_agent_reviews_explain_the_cause_and_keep_the_card(self):
        self.refresh()
        self.organize("asset-b", action="ADD_TAGS", tags="x")
        card = self.owner.review_id
        owner = self.session.asset_organization
        # Local MCP shares the bounded review pool; a bound of 2 stands for 31 agent reviews.
        self.enterContext(patch.object(owner.reviews, "_limit", 2))
        agent = owner.prepare("update_tags", asset_ids=["asset-a"], add_tags=["agent"])
        self.settle()
        reads = len(self.service.requests)
        cls, operator, context, _ = self.dialog("asset-a", action="ADD_TAGS", tags="y")
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        message = operator.report.call_args.args[1]
        self.assertIn("connected agent", message)
        self.assertIn("expire after 10 minutes", message)
        self.assertNotIn("before preparing another", message)
        self.assertEqual(self.owner.review_id, card)
        self.assertEqual(self.owner.review["phase"], "READY")
        self.assertEqual(len(self.service.requests), reads)
        # Once the agent's review is discarded, Organize prepares again.
        owner.discard(agent)
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.settle()
        self.assertEqual(self.owner.review["phase"], "READY")
        self.assertNotEqual(self.owner.review_id, card)
        self.assertEqual(self.service.writes, [])
