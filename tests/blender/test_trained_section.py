# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Trained models section, project defaults and composer label through the installed ZIP (#97).

These tests reuse the synthetic service of test_trained_models: the captured
public FLUX.1 Dev and Z-Image bases, public LoRAs and a composition, plus
synthetic private records. Nothing reaches the network and no paid request is
possible: only list, description and dryRun quote requests are answered.
"""

import copy
import sqlite3
import types
import unittest
from unittest.mock import patch

import bpy
import test_trained_models as trained_tests
from helpers import submodule

FLUX1 = trained_tests.FLUX1
ZIMAGE = trained_tests.ZIMAGE
LORA_A = trained_tests.LORA_A
COMPOSITION = trained_tests.COMPOSITION
STUDIO_LORA = trained_tests.STUDIO_LORA
STACK_LABEL = "FLUX.1 Dev · Studio LoRA (+1)"


class RecordingLayout:
    """Like test_model_picker.FakeLayout, but keeps the properties set on each operator."""

    CONTAINERS = ("row", "column", "box", "split", "grid_flow")

    def __init__(self, kind="layout", **kwargs):
        self.kind, self.kwargs, self.children, self.calls = kind, kwargs, [], []
        self.alignment, self.enabled, self.active = "EXPAND", True, True

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            if name in self.CONTAINERS:
                child = RecordingLayout(name, **kwargs)
                self.children.append(child)
                return child
            result = types.SimpleNamespace() if name == "operator" else None
            self.calls.append((name, args, kwargs, result))
            return result

        return call

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def ops(self, idname):
        """[(enabled, properties)] for each button of this operator, in draw order."""
        return [
            (node.enabled, vars(call[3]))
            for node in self.walk()
            for call in node.calls
            if call[0] == "operator" and call[1][0] == idname
        ]

    def labels(self):
        return [
            (call[2].get("text"), call[2].get("icon"))
            for node in self.walk()
            for call in node.calls
            if call[0] == "label"
        ]

    def text(self):
        return " ".join(text for text, _icon in self.labels() if text)

    def props(self):
        return [
            (call[1][1], call[2].get("text"))
            for node in self.walk()
            for call in node.calls
            if call[0] == "prop"
        ]


def _shared(name):
    """A helper of test_trained_models' tests, without binding that TestCase here.

    Binding the class in this module would make discovery run its tests twice.
    """
    return getattr(trained_tests.TrainedModelTests, name)


class TrainedSectionTests(unittest.TestCase):
    setUp = _shared("setUp")
    settle = _shared("settle")
    load_catalog = _shared("load_catalog")
    open_trained = _shared("open_trained")
    highlight = _shared("highlight")
    pick = _shared("pick")
    body = _shared("body")
    gets = _shared("gets")

    # -- helpers -------------------------------------------------------------------
    @property
    def defaults(self):
        return submodule("blender.trained_defaults")

    def section(self, lane="image", lane_state=None):
        root = RecordingLayout()
        lane_state = lane_state or self.scene.scenario.lane_state(lane)
        submodule("blender.panels").draw_model_row(root, lane_state, lane)
        return root

    @staticmethod
    def snapshot(lane_state):
        return (
            lane_state.model_id,
            lane_state.model_key,
            [
                (s.model_id, s.kind, round(s.scale, 4), s.has_scale, s.fmin, s.fmax)
                for s in lane_state.trained
            ],
            lane_state.estimate_state,
        )

    def choose_stack(self):
        """FLUX.1 Dev with the private Studio LoRA at 0.8 and a public LoRA at 1.25."""
        self.load_catalog()
        self.open_trained()
        self.pick(STUDIO_LORA, 0.8)
        self.open_trained()
        self.pick(LORA_A, 1.25)

    def save_default(self, lane="image"):
        view = self.defaults.view(self.scene.scenario.lane_state(lane), lane)
        self.assertTrue(view.loaded and view.can_save, view)
        result = bpy.ops.scenario.trained_default_save(
            lane=lane, context_id=view.context, revision=view.revision
        )
        self.assertEqual(result, {"FINISHED"})
        return self.runtime.ensure_model_defaults().lane(lane)

    def release(self, lane_state, model_id=ZIMAGE):
        """A form with no explicit choice, as in a new scene: no model chosen, no trained model."""
        lane_state.trained.clear()
        lane_state.model_id = model_id
        lane_state.model_key = ""

    def errors(self, lane="image"):
        return self.generation.build_request(self.scene, lane, for_estimate=True).errors

    # -- strengths -----------------------------------------------------------------
    def test_section_bounds_each_lora_strength_and_keeps_scales_aligned(self):
        self.choose_stack()
        before = self.snapshot(self.lane)
        root = self.section()
        self.assertEqual(before, self.snapshot(self.lane))  # drawing changes nothing
        self.assertIn(("Trained models", "SHADERFX"), root.labels())
        self.assertIn(("Studio LoRA", "SHADERFX"), root.labels())
        self.assertEqual(
            [prop for prop in root.props() if prop[0] == "scale"],
            [("scale", "Strength (0 to 2)"), ("scale", "Strength (0 to 2)")],
        )
        self.assertEqual(
            [props for _enabled, props in root.ops("scenario.trained_remove")],
            [{"lane": "image", "index": 0}, {"lane": "image", "index": 1}],
        )
        self.assertEqual(
            [props for _enabled, props in root.ops("scenario.pick_model")][-1],
            {"lane": "image", "category": "trained"},
        )
        self.assertIn(
            ("Experimental: LoRAs and compositions not accepted", "EXPERIMENTAL"), root.labels()
        )
        self.lane.estimate_state = "READY"
        self.lane.trained[1].scale = 0.35
        self.assertEqual(self.lane.estimate_state, "PENDING")
        body = self.body()
        self.assertEqual((body["loras"], body["lorasScale"]), ([STUDIO_LORA, LORA_A], [0.8, 0.35]))
        self.lane.trained[0].scale = 7.0
        self.assertEqual(round(self.lane.trained[0].scale, 4), 2.0)  # the declared maximum
        self.assertEqual(self.body()["lorasScale"], [2.0, 0.35])
        self.assertEqual(bpy.ops.scenario.trained_remove(lane="image", index=0), {"FINISHED"})
        body = self.body()
        self.assertEqual((body["loras"], body["lorasScale"]), ([LORA_A], [0.35]))

    def test_a_lora_without_strength_gets_one_only_by_an_explicit_action(self):
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        self.lane.model_id = FLUX1
        slot = self.lane.trained.add()
        slot.model_id, slot.kind, slot.lane, slot.name = LORA_A, "lora", "image", "Public LoRA"
        slot[self.trained.SCOPE] = self.trained.current_scope()
        self.assertEqual(self.errors(), ["LoRA Scale: provide a strength for each LoRA."])
        root = self.section()
        self.assertNotIn("scale", [name for name, _text in root.props()])
        self.assertEqual(
            root.ops("scenario.trained_set_strength"), [(True, {"lane": "image", "index": 0})]
        )
        self.assertIn("LoRA Scale: provide a strength for each LoRA.", root.text())
        self.assertIn(("LoRA Scale: provide a strength for", "ERROR"), root.labels())
        self.lane.estimate_state = "READY"
        self.assertEqual(bpy.ops.scenario.trained_set_strength(lane="image", index=0), {"FINISHED"})
        self.assertEqual(
            (slot.has_scale, slot.fmin, slot.fmax, round(slot.scale, 4)), (True, 0.0, 2.0, 1.0)
        )
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertEqual(self.body()["lorasScale"], [1.0])
        self.assertEqual(
            bpy.ops.scenario.trained_set_strength(lane="image", index=4), {"CANCELLED"}
        )

    def test_a_declared_default_strength_is_sent_without_a_control(self):
        flux1 = copy.deepcopy(self.details[FLUX1])
        for field in flux1["inputs"]:
            if field["name"] == "lorasScale":
                field.pop("min"), field.pop("max")
                field["default"] = 0.7
        self.details[FLUX1] = flux1
        self.load_catalog()
        self.open_trained()
        self.highlight(LORA_A)
        self.assertEqual(bpy.ops.scenario.pick_model(lane="image"), {"FINISHED"})
        (slot,) = self.lane.trained
        self.assertFalse(slot.has_scale)
        self.assertEqual(self.body()["lorasScale"], [0.7])
        root = self.section()
        self.assertIn(("Strength: the base model's default (0.7)", "BLANK1"), root.labels())
        self.assertEqual(root.ops("scenario.trained_set_strength"), [])

    def test_strength_fields_follow_the_range_the_base_declares_now(self):
        self.load_catalog()
        self.open_trained()
        self.pick(LORA_A, 1.5)
        narrowed = copy.deepcopy(self.details[FLUX1])
        for field in narrowed["inputs"]:
            if field["name"] == "lorasScale":
                field["max"] = 1.2
        catalog = submodule("core.api.catalog")
        self.generation.set_models([catalog.ModelRecord.from_api(narrowed)], {}, mark_dirty=False)
        (slot,) = self.lane.trained
        self.assertEqual((slot.fmin, round(slot.fmax, 4)), (0.0, 1.2))
        self.assertEqual(round(slot.scale, 4), 1.5)  # kept, never changed silently
        self.assertEqual(self.errors(), ["LoRA Scale: use a strength from 0 to 1.2."])
        self.assertIn(("scale", "Strength (0 to 1.2)"), self.section().props())
        slot.scale = 1.5
        self.assertEqual(round(slot.scale, 4), 1.2)
        self.assertEqual(self.body()["lorasScale"], [1.2])

    def test_composition_concepts_are_listed_read_only(self):
        self.load_catalog()
        self.open_trained()
        self.pick(COMPOSITION)
        root = self.section()
        self.assertIn((f"{self.lane.trained[0].name} (composition)", "GROUP"), root.labels())
        concepts = self.runtime.state.trained_records[COMPOSITION].raw["concepts"]
        count = len(concepts)
        self.assertIn(
            (f"Combines {count} LoRA{'s' if count != 1 else ''}:", "BLANK1"), root.labels()
        )
        self.assertNotIn("scale", [name for name, _text in root.props()])
        self.assertEqual(root.ops("scenario.trained_set_strength"), [])

    # -- project defaults ----------------------------------------------------------
    def test_saving_a_default_changes_no_payload_and_needs_the_reviewed_revision(self):
        self.choose_stack()
        self.defaults.load()
        root = self.section()
        self.assertIn(("No project default for this form", "UNPINNED"), root.labels())
        view = self.defaults.view(self.lane, "image")
        (save,) = root.ops("scenario.trained_default_save")
        self.assertEqual(save, (True, {"lane": "image", "context_id": view.context, "revision": 0}))
        self.assertFalse(root.ops("scenario.trained_default_apply")[0][0])  # nothing to use
        self.assertFalse(root.ops("scenario.trained_default_clear")[0][0])
        self.lane.estimate_state = "READY"
        body = self.body()
        state = self.save_default()
        store = submodule("core.jobs.store")
        self.assertEqual(state.revision, 1)
        self.assertEqual(
            state.default,
            store.TrainedModelDefault(
                "image",
                "stack",
                FLUX1,
                (
                    store.TrainedModelPick(STUDIO_LORA, 0.8),
                    store.TrainedModelPick(LORA_A, 1.25),
                ),
            ),
        )
        self.assertEqual(self.lane.estimate_state, "READY")  # saving prices nothing
        self.assertEqual(self.body(), body)
        stale = bpy.ops.scenario.trained_default_save(
            lane="image", context_id=view.context, revision=0
        )
        self.assertEqual(stale, {"CANCELLED"})
        foreign = bpy.ops.scenario.trained_default_save(
            lane="image", context_id="another-selection", revision=1
        )
        self.assertEqual(foreign, {"CANCELLED"})
        self.assertEqual(self.runtime.ensure_model_defaults().lane("image").revision, 1)
        view = self.defaults.view(self.lane, "image")
        self.assertEqual((view.label, view.in_use, view.can_save), (STACK_LABEL, True, False))
        text = self.section().text()
        self.assertIn("Project default:", text)
        self.assertIn("This form uses the project default", text)

    def test_saving_refuses_a_choice_that_cannot_run(self):
        self.load_catalog()
        self.open_trained()
        self.pick(LORA_A, 0.8)
        self.lane.model_id = ZIMAGE  # keeps the LoRA, which Z-Image refuses
        self.defaults.load()
        view = self.defaults.view(self.lane, "image")
        self.assertFalse(view.can_save)
        result = bpy.ops.scenario.trained_default_save(
            lane="image", context_id=view.context, revision=view.revision
        )
        self.assertEqual(result, {"CANCELLED"})
        self.assertIsNone(self.runtime.ensure_model_defaults().lane("image").default)

    def test_use_applies_the_default_to_a_form_with_another_choice(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        self.lane.trained.clear()
        self.lane.model_id = ZIMAGE
        self.lane.estimate_state = "READY"
        (use,) = self.section().ops("scenario.trained_default_apply")
        self.assertTrue(use[0])
        self.assertEqual(bpy.ops.scenario.trained_default_apply(lane="image"), {"FINISHED"})
        self.assertEqual((self.lane.model_id, self.lane.model_key), (FLUX1, FLUX1))
        self.assertEqual(
            [(s.model_id, round(s.scale, 4), s.get(self.trained.SCOPE)) for s in self.lane.trained],
            [
                (STUDIO_LORA, 0.8, self.trained.current_scope()),
                (LORA_A, 1.25, self.trained.current_scope()),
            ],
        )
        self.assertEqual(self.lane.estimate_state, "PENDING")
        body = self.body()
        self.assertEqual((body["loras"], body["lorasScale"]), ([STUDIO_LORA, LORA_A], [0.8, 1.25]))
        self.assertFalse(self.section().ops("scenario.trained_default_apply")[0][0])  # in use

    def test_a_composition_default_runs_alone(self):
        self.load_catalog()
        self.open_trained()
        self.pick(COMPOSITION)
        self.defaults.load()
        state = self.save_default()
        self.assertEqual(state.default.route, "composition")
        self.assertEqual([pick.scale for pick in state.default.picks], [None])
        self.release(self.lane)
        self.assertTrue(self.defaults.apply_pending())
        self.assertEqual(self.body()["modelId"], COMPOSITION)
        self.assertNotIn("loras", self.body())

    def test_a_form_without_a_choice_takes_the_default_before_any_price(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        self.release(self.lane)
        second = bpy.data.scenes.new("Second shot")
        self.addCleanup(bpy.data.scenes.remove, second)
        self.assertEqual(
            self.errors(),
            [f"Applying the project default {STACK_LABEL}: applying it to the form."],
        )
        self.posts.clear()
        self.generation.request_estimate(self.scene, "image")
        self.assertEqual(self.lane.estimate_state, "UNAVAILABLE")
        self.assertEqual(self.posts, [])  # never priced as the base model alone
        self.assertTrue(self.defaults.apply_pending())
        for scene in (self.scene, second):
            lane_state = scene.scenario.lane_state("image")
            self.assertEqual((lane_state.model_id, lane_state.model_key), (FLUX1, FLUX1))
            self.assertEqual(
                [s.model_id for s in lane_state.trained], [STUDIO_LORA, LORA_A], scene.name
            )
            self.assertEqual(lane_state.estimate_state, "PENDING")
        self.assertEqual(self.body()["lorasScale"], [0.8, 1.25])
        # A form with an explicit choice is never changed by the default.
        self.lane.model_id = ZIMAGE
        self.lane.trained.clear()
        self.assertFalse(self.defaults.apply_pending())
        self.assertEqual(self.lane.model_id, ZIMAGE)

    def test_an_unavailable_default_blocks_the_price_until_a_choice_or_clear(self):
        self.choose_stack()
        self.defaults.load()
        state = self.save_default()
        self.private = [record for record in self.private if record["id"] != STUDIO_LORA]
        self.trained.request(self.runtime.ensure_manager(), self.runtime.ensure_catalog())
        self.settle()
        self.release(self.lane)
        self.lane.estimate_state = "IDLE"
        self.defaults.apply_pending()  # reprices the blocked form, applies nothing
        self.assertFalse(len(self.lane.trained))
        self.assertEqual(self.lane.model_key, "")
        self.assertEqual(self.lane.estimate_state, "PENDING")  # its blocked price is current
        label = f"FLUX.1 Dev · {STUDIO_LORA} (+1)"
        reason = (
            f"Project default {label} is unavailable: choose a model or clear the default. "
            "A trained model it names is no longer listed."
        )
        self.assertEqual(self.errors(), [reason])
        self.posts.clear()
        self.generation.request_estimate(self.scene, "image")
        self.assertEqual(self.lane.estimate_state, "UNAVAILABLE")
        self.assertEqual(self.lane.estimate_error, reason)
        self.assertEqual(self.posts, [])
        root = self.section()
        self.assertFalse(root.ops("scenario.trained_default_apply")[0][0])
        self.assertIn("is unavailable", root.text())
        self.assertEqual(bpy.ops.scenario.trained_default_apply(lane="image"), {"CANCELLED"})
        # Choosing a model is an explicit choice; the default no longer decides the form.
        self.lane.model_id = FLUX1
        self.assertEqual(self.errors(), [])
        self.release(self.lane)
        self.assertEqual(self.errors(), [reason])
        self.lane.estimate_state = "UNAVAILABLE"
        view = self.defaults.view(self.lane, "image")
        cleared = bpy.ops.scenario.trained_default_clear(
            lane="image", context_id=view.context, revision=state.revision
        )
        self.assertEqual(cleared, {"FINISHED"})
        self.assertIsNone(self.runtime.ensure_model_defaults().lane("image").default)
        self.assertEqual(self.lane.estimate_state, "PENDING")  # repriced without the default
        self.assertEqual(self.errors(), [])
        stale = bpy.ops.scenario.trained_default_clear(
            lane="image", context_id=view.context, revision=state.revision
        )
        self.assertEqual(stale, {"CANCELLED"})

    def test_an_unreadable_saved_default_blocks_governed_forms_and_is_preserved(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        database = self.runtime.state.job_store._path
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE trained_defaults SET record='{}' WHERE lane='image'")
        connection.close()
        before = database.read_bytes()
        cache = self.defaults.load(force=True)
        self.assertIn("image", cache.errors)
        self.release(self.lane)
        reason = (
            "Could not read the project default: Stored trained-model default is invalid; "
            "preserve its database for recovery. Choose a model to continue."
        )
        self.assertEqual(self.errors(), [reason])
        self.defaults.apply_pending()
        self.assertEqual(self.lane.model_key, "")  # nothing applied, nothing reset
        root = self.section()
        self.assertIn("Could not read the project default", root.text())
        self.assertFalse(root.ops("scenario.trained_default_save")[0][0])
        self.assertFalse(root.ops("scenario.trained_default_clear")[0][0])
        self.assertEqual(database.read_bytes(), before)
        # The Render Image form's default stays readable on its own.
        self.assertNotIn("render_image", cache.errors)

    def test_defaults_belong_to_the_credentials_and_project_that_saved_them(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        old = self.defaults.view(self.lane, "image")
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        self.prefs.project_id = "project-b"
        self.runtime.sync_catalog_context()
        self.assertIsNone(self.defaults.cached())
        self.load_catalog()
        self.defaults.load()
        self.assertIsNone(self.defaults.view(self.lane, "image").default)
        self.release(self.lane)
        self.assertFalse(self.defaults.apply_pending())
        self.assertEqual(self.lane.model_key, "")  # nothing from the other project
        self.assertNotIn("project default", " ".join(self.errors()))
        self.lane.model_id = FLUX1
        moved = bpy.ops.scenario.trained_default_clear(
            lane="image", context_id=old.context, revision=old.revision
        )
        self.assertEqual(moved, {"CANCELLED"})  # reviewed under the other project
        self.prefs.project_id = ""
        self.runtime.sync_catalog_context()
        self.load_catalog()
        self.defaults.load()
        self.assertEqual(self.defaults.view(self.lane, "image").label, STACK_LABEL)

    def test_render_form_takes_its_default_for_local_mcp_too(self):
        self.load_catalog()
        render = self.scene.scenario.lane_state("render_image")
        self.open_trained("render_image")
        self.highlight(LORA_A)
        self.wm.scenario_picker_strength = 0.6
        self.assertEqual(bpy.ops.scenario.pick_model(lane="render_image"), {"FINISHED"})
        self.assertEqual(render.model_id, FLUX1)
        self.defaults.load()
        self.save_default("render_image")
        self.release(render, render.model_id)
        tools = submodule("mcp.tools_scenario")
        result = tools.render_form({"lane": "render_image"})
        self.assertEqual(result["model_id"], FLUX1)
        self.assertEqual(
            result["trained_models"], [{"model_id": LORA_A, "kind": "lora", "strength": 0.6}]
        )
        self.assertEqual(render.model_key, FLUX1)

    def test_naming_the_shown_render_model_through_mcp_is_an_explicit_choice(self):
        self.load_catalog()
        render = self.scene.scenario.lane_state("render_image")
        self.open_trained("render_image")
        self.highlight(LORA_A)
        self.wm.scenario_picker_strength = 0.6
        self.assertEqual(bpy.ops.scenario.pick_model(lane="render_image"), {"FINISHED"})
        self.defaults.load()
        self.save_default("render_image")
        self.release(render, FLUX1)  # the default's base is already shown, without its LoRA
        tools = submodule("mcp.tools_scenario")
        result = tools.render_form(
            {"lane": "render_image", "action": "configure", "settings": {"model_id": FLUX1}}
        )
        self.assertEqual((result["model_id"], result["trained_models"]), (FLUX1, []))
        self.assertEqual((render.model_key, len(render.trained)), (FLUX1, 0))
        self.assertNotIn("project default", " ".join(result["errors"]).lower())
        # Settings that name no model leave a form without a choice to its default.
        self.release(render, FLUX1)
        result = tools.render_form(
            {"lane": "render_image", "action": "configure", "settings": {"look": "dusk"}}
        )
        self.assertEqual(
            result["trained_models"], [{"model_id": LORA_A, "kind": "lora", "strength": 0.6}]
        )

    def test_a_default_saved_in_one_scene_reprices_no_other_scene(self):
        self.choose_stack()
        self.defaults.load()
        second = bpy.data.scenes.new("Second shot")
        self.addCleanup(bpy.data.scenes.remove, second)
        self.lane.estimate_state = "READY"
        body = self.body()
        self.save_default()
        other = second.scenario.lane_state("image")
        self.assertEqual(
            (other.model_key, [s.model_id for s in other.trained]), (FLUX1, [STUDIO_LORA, LORA_A])
        )
        self.assertEqual(other.estimate_state, "PENDING")
        self.assertEqual(self.lane.estimate_state, "READY")  # the saving form is not repriced
        self.assertEqual(self.body(), body)
        other.trained[0].scale = 0.5  # editing that scene's strength reprices only that scene
        self.assertEqual(self.lane.estimate_state, "READY")

    def test_a_blocked_form_keeps_its_reason_without_repricing_again(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        self.private = [record for record in self.private if record["id"] != STUDIO_LORA]
        self.trained.request(self.runtime.ensure_manager(), self.runtime.ensure_catalog())
        self.settle()
        self.release(self.lane)
        form = submodule("blender.reference_form")
        ref = self.lane.references.add()
        ref.source, ref.asset_id = "ASSET", "asset_from_another_scope"
        ref[form._SCOPE], ref[form._ASSET] = "another-scope", ref.asset_id
        reason = self.errors()[0]
        self.assertTrue(reason.startswith("Project default "), reason)
        self.lane.estimate_state = "IDLE"
        self.assertTrue(self.defaults.apply_pending())  # its price did not show the reason
        self.generation.request_estimate(self.scene, "image")
        self.assertEqual(
            (self.lane.estimate_state, self.lane.estimate_error), ("UNAVAILABLE", reason)
        )
        self.assertFalse(self.defaults.apply_pending())  # current: no repricing loop
        self.assertEqual(self.lane.estimate_state, "UNAVAILABLE")

    def test_a_default_lands_only_on_a_base_its_form_lists(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        self.release(self.lane)
        self.runtime.set_enum_items(("models", "image"), [(ZIMAGE, "Z-Image", "")])
        self.defaults.apply_pending()
        self.assertEqual((self.lane.model_id, self.lane.model_key), (ZIMAGE, ""))
        self.assertFalse(len(self.lane.trained))
        self.assertIn("Its base model is not in this form's model list.", self.errors()[0])
        self.assertEqual(bpy.ops.scenario.trained_default_apply(lane="image"), {"CANCELLED"})
        self.assertFalse(len(self.lane.trained))

    def test_a_base_described_without_inputs_is_read_once(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        catalog = submodule("core.api.catalog")
        self.details[FLUX1] = trained_tests.row(self.details[FLUX1])
        self.runtime.state.records[FLUX1] = catalog.ModelRecord.from_api(self.details[FLUX1])
        self.release(self.lane)
        render = self.scene.scenario.lane_state("render_image")
        render.model_id = ZIMAGE  # no form shows the base whose description changed
        reads = len(self.gets(FLUX1))
        for _tick in range(3):
            self.defaults.apply_pending()
            self.settle()
        self.assertEqual(len(self.gets(FLUX1)), reads + 1)
        self.assertFalse(len(self.lane.trained))
        self.assertIn("Its base model's description declares no inputs.", self.errors()[0])

    def test_the_pump_applies_defaults_before_pricing_and_survives_a_failure(self):
        self.choose_stack()
        self.defaults.load()
        self.save_default()
        self.release(self.lane)
        pump = submodule("blender.pump")
        self.addCleanup(pump._failures.clear)
        pump._failures.clear()
        pump._process()  # the catalog is loaded, so this tick only applies and prices
        self.assertEqual((self.lane.model_key, len(self.lane.trained)), (FLUX1, 2))
        self.release(self.lane)
        with (
            patch.object(self.defaults, "apply_pending", side_effect=RuntimeError("synthetic")),
            self.assertLogs("scenario.pump", "ERROR") as logs,
        ):
            pump._process()
            pump._process()
        self.assertEqual(len(logs.records), 1)  # reported once per failure type
        self.assertEqual(self.lane.model_key, "")

    # -- compact composer and job views ----------------------------------------------
    def test_composer_chip_and_job_views_name_the_trained_choice(self):
        self.choose_stack()
        panels = submodule("blender.panels")
        self.assertEqual(panels.model_button_text(self.lane), STACK_LABEL)
        self.assertEqual(panels.model_chip_parts(self.lane), ("FLUX.1 Dev", "Studio LoRA", 1))
        self.assertEqual(panels.model_chip_category(self.lane, "image"), "trained")
        video = self.scene.scenario.lane_state("video")
        self.assertEqual(panels.model_chip_category(video, "video"), "all")
        draw = submodule("blender.composer.draw")
        with patch.object(self.runtime, "message_visible", return_value=""):
            self.assertEqual(draw.status_note(self.lane), draw.STRENGTH_HINT)
        with patch.object(self.runtime, "message_visible", return_value="Saved"):
            self.assertEqual(draw.status_note(self.lane), "Saved")
        meta = self.generation.request_meta(bpy.context, "image")
        self.assertEqual(meta["model_name"], STACK_LABEL)
        self.assertEqual(
            meta["trained_models"],
            [
                {"model_id": STUDIO_LORA, "name": "Studio LoRA", "kind": "lora", "strength": 0.8},
                {
                    "model_id": LORA_A,
                    "name": self.lane.trained[1].name,
                    "kind": "lora",
                    "strength": 1.25,
                },
            ],
        )
        self.lane.trained.clear()
        self.assertEqual(panels.model_button_text(self.lane), "FLUX.1 Dev")
        self.assertNotIn("trained_models", self.generation.request_meta(bpy.context, "image"))
