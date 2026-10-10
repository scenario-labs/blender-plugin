# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved-job action descriptors shared by native result surfaces, without Blender."""

import ast
import itertools
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.core.scene.panorama import WORLD_MEDIA_TYPES
from scenario.core.ui import saved_job_actions as sja

ROOT = Path(__file__).resolve().parents[2]
TYPES = sja.ResultTypes(
    model="model/gltf-binary",
    media={"video/mp4": "video", "video/webm": "video", "audio/wav": "audio"},
    world=WORLD_MEDIA_TYPES,
)
CONTEXT = "context-token"
JOB = (("context_id", CONTEXT), ("request_id", "request"), ("expected_revision", 7))


def view(actions=(), state="remote", assets=(), **meta):
    return SimpleNamespace(
        local_id="request",
        asset_ids=[asset_id for asset_id, _ in assets],
        asset_types=dict(assets),
        meta={
            "shared_job": True,
            "saved_revision": 7,
            "saved_state": state,
            "recovery_actions": tuple(actions),
            **meta,
        },
    )


def rows(items):
    """Compact golden form: (key, group, operator, label, icon, properties)."""
    return [
        (item.key, item.group, item.operator, item.label, item.icon, dict(item.properties))
        for item in items
    ]


def recover(action, group):
    return (
        action,
        group,
        "scenario.recover_job",
        sja.LABELS[action],
        "NONE",
        dict(JOB, action=action),
    )


def asset(action, operator, label, asset_id, **extra):
    return (
        f"{action}:{asset_id}",
        "apply",
        operator,
        label,
        "NONE",
        dict(JOB, asset_id=asset_id, **extra),
    )


APPLICATION_ACTIONS = (
    "import_images",
    "import_media",
    "import_model",
    "apply_world",
    "restore_world",
    "apply_material",
    "apply_mesh",
    "apply_mesh_source",
)
VOCABULARY = (*sja.RECOVERY_ACTIONS, *APPLICATION_ACTIONS, "recover_blockout")
ASSETS = (
    ("clip", "video/webm"),
    ("panorama", "image/exr"),
    ("mesh", "model/gltf-binary"),
)
AWAITING = (
    "awaiting_review",
    "status",
    None,
    "Downloaded result awaits application review",
    "INFO",
    {},
)
REUSE = ("reuse", "status", None, "Reuse saved results", "FILE_REFRESH", {})


def test_unshared_or_unprojected_views_offer_nothing():
    assert sja.describe(view(("refresh",), shared_job=False), CONTEXT, TYPES) == ()
    unprojected = view(("refresh",))
    del unprojected.meta["saved_revision"]
    assert sja.describe(unprojected, CONTEXT, TYPES) == ()
    assert sja.describe(view(()), CONTEXT, TYPES) == ()


def test_recovery_controls_dispatch_the_recovery_operator_with_their_action():
    items = sja.describe(view(("refresh", "resume", "cancel")), CONTEXT, TYPES)
    assert rows(items) == [
        recover("refresh", "recover"),
        recover("resume", "recover"),
        recover("cancel", "cancel"),
    ]
    for action, group in (
        ("cancel_prepared", "cancel"),
        ("recover_download", "recover"),
        ("retry_receipt", "receipt"),
    ):
        state = "prepared" if action == "cancel_prepared" else "downloading"
        assert rows(sja.describe(view((action,), state), CONTEXT, TYPES)) == [
            recover(action, group)
        ]
    assert sja.LABELS["cancel_prepared"] == "Cancel prepared job"
    assert sja.LABELS["cancel"] == "Cancel generation"


def test_ready_images_offer_import_world_and_material_then_await_review():
    assets = (
        ("first", "image/png"),
        ("depth", "image/webp"),
        ("second", "image/jpeg"),
        ("third", "image/x-exr"),
    )
    actions = ("import_images", "apply_world", "apply_material")
    items = sja.describe(view(actions, "ready", assets), CONTEXT, TYPES)
    world = "scenario.apply_saved_world"
    assert rows(items) == [
        ("import_images", "apply", "scenario.import_saved_images", "Import saved images", "NONE", dict(JOB)),
        # World numbering counts only panorama candidates, unlike per-asset imports.
        asset("apply_world", world, "Set panorama as World (1)", "first", purpose="world"),
        asset("apply_world", world, "Set panorama as World (2)", "second", purpose="world"),
        asset("apply_world", world, "Set panorama as World (3)", "third", purpose="world"),
        ("apply_material", "apply", "scenario.apply_saved_material", "Apply saved material", "NONE", dict(JOB)),
        AWAITING,
    ]  # fmt: skip


def test_media_and_model_controls_number_every_saved_asset():
    assets = (
        ("clip", "video/mp4"),
        ("texture", "image/png"),
        ("sound", "audio/wav"),
        ("mesh", "model/gltf-binary"),
        ("unknown", None),
        ("variant", "model/gltf-binary"),
    )
    actions = ("import_media", "import_model", "apply_mesh", "apply_mesh_source")
    items = sja.describe(view(actions, "apply_failed", assets), CONTEXT, TYPES)
    media, model, mesh = (
        "scenario.import_saved_media",
        "scenario.import_saved_model",
        "scenario.apply_saved_mesh",
    )
    assert rows(items) == [
        asset("import_media", media, "Add video strip (1)", "clip"),
        asset("import_media", media, "Add audio strip (3)", "sound"),
        asset("import_model", model, "Import model (4)", "mesh"),
        asset("import_model", model, "Import model (6)", "variant"),
        asset("apply_mesh", mesh, "Apply mesh edit (4)", "mesh", original_source=False),
        asset("apply_mesh", mesh, "Apply mesh edit (6)", "variant", original_source=False),
        asset(
            "apply_mesh_source",
            mesh,
            "Apply to captured source (4)",
            "mesh",
            original_source=True,
        ),
        asset(
            "apply_mesh_source",
            mesh,
            "Apply to captured source (6)",
            "variant",
            original_source=True,
        ),
        AWAITING,
    ]


def test_applied_results_show_reuse_only_with_a_reuse_action():
    restore = (
        "restore_world",
        "apply",
        "scenario.apply_saved_world",
        "Restore previous World",
        "NONE",
        dict(JOB, asset_id="", purpose="restore_world"),
    )
    only_restore = sja.describe(view(("restore_world", "retry_receipt"), "applied"), CONTEXT, TYPES)
    assert rows(only_restore) == [restore, recover("retry_receipt", "receipt")]
    reuse = sja.describe(
        view(("import_images", "restore_world"), "applied", (("a", "image/png"),)),
        CONTEXT,
        TYPES,
    )
    assert rows(reuse)[0] == REUSE
    assert rows(reuse)[-1] == restore
    assert [item.key for item in reuse] == ["reuse", "import_images", "restore_world"]


@pytest.mark.parametrize(
    ("review", "expected"),
    [
        (
            None,
            [
                (
                    "recover_blockout",
                    "recover",
                    "scenario.read_saved_blockout",
                    "Read saved Blockout plan",
                    "NONE",
                    dict(JOB),
                )
            ],
        ),
        (
            SimpleNamespace(task=object(), phase="READING", identifier="review"),
            [
                (
                    "recover_blockout:reading",
                    "status",
                    None,
                    "Reading saved plan...",
                    "TIME",
                    {},
                )
            ],
        ),
        (
            SimpleNamespace(task=None, phase="READY", identifier="review"),
            [
                (
                    "recover_blockout:use",
                    "apply",
                    "scenario.use_saved_blockout",
                    "Use saved Blockout plan",
                    "NONE",
                    {"context_id": CONTEXT, "review_id": "review"},
                )
            ],
        ),
        (
            SimpleNamespace(task=None, phase="ERROR", identifier="review"),
            [
                (
                    "recover_blockout:error",
                    "status",
                    None,
                    "Plan needs review; check job and destination",
                    "ERROR",
                    {},
                ),
                (
                    "recover_blockout",
                    "recover",
                    "scenario.read_saved_blockout",
                    "Read saved Blockout plan",
                    "NONE",
                    dict(JOB),
                ),
            ],
        ),
    ],
)
def test_blockout_recovery_follows_the_current_scene_review(review, expected):
    items = sja.describe(view(("recover_blockout",), "succeeded"), CONTEXT, TYPES, review)
    assert rows(items) == expected
    assert all(item.action == "recover_blockout" for item in items)


def test_every_offered_action_is_described_with_unique_keys_and_its_action_name():
    for state, length in itertools.product(("ready", "applied"), (1, 2)):
        for actions in itertools.combinations(VOCABULARY, length):
            items = sja.describe(view(actions, state, ASSETS), CONTEXT, TYPES)
            keys = [item.key for item in items]
            assert len(keys) == len(set(keys)), actions
            offered = {item.action for item in items if item.operator is not None}
            assert offered == set(actions), actions
            for item in items:
                assert item.group in {"recover", "cancel", "apply", "receipt", "status"}
                assert (item.operator is None) == (item.group == "status")
                if item.operator is not None:
                    assert dict(item.properties)["context_id"] == CONTEXT
                    assert item.icon == "NONE" and "_" not in item.label


def test_unknown_actions_fail_instead_of_disappearing():
    with pytest.raises(ValueError, match="describes action 'import_everything'"):
        sja.describe(view(("import_everything",)), CONTEXT, TYPES)


def test_descriptors_are_immutable_and_reading_does_not_change_the_view():
    subject = view(("import_model",), "ready", (("mesh", "model/gltf-binary"),))
    before = (list(subject.asset_ids), dict(subject.asset_types), dict(subject.meta))
    item = sja.describe(subject, CONTEXT, TYPES)[0]
    with pytest.raises(AttributeError):
        item.label = "Changed"
    assert (subject.asset_ids, subject.asset_types, subject.meta) == before
    # Result types hold a mapping yet stay usable as a key, by identity.
    assert {TYPES: True}[TYPES] and TYPES != sja.ResultTypes(TYPES.model, {}, frozenset())


def _mcp_spec(name):
    """One registered MCP tool's description and its literal schema properties node."""
    tree = ast.parse((ROOT / "scenario/mcp/tools_scenario.py").read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "ToolSpec"
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == name
        ):
            description = "".join(
                part.value for part in ast.walk(node.args[1]) if isinstance(part, ast.Constant)
            )
            return description, node.args[2].args[0]
    raise AssertionError(f"{name} is not registered")


def test_native_recovery_actions_match_the_mcp_action_names():
    schema = ast.literal_eval(_mcp_spec("recover_local_job")[1])
    control = [action for action in sja.RECOVERY_ACTIONS if action != "cancel_prepared"]
    assert schema["action"]["enum"] == control
    description, _ = _mcp_spec("job_status")
    mapping = re.search(r"actions name explicit follow-ups[^.]*\.", description).group(0)
    assert "cancel_prepared maps to the cancel_prepared_job tool" in mapping
    named = re.search(r"; (.+) map to recover_local_job", mapping).group(1)
    assert re.split(r", | and ", named) == control


def _mcp_purpose(item):
    """The prepare_result_application purpose for the same native application."""
    properties = dict(item.properties)
    if item.operator == "scenario.apply_saved_world":
        return properties["purpose"]
    if item.operator == "scenario.apply_saved_mesh":
        return "mesh_source" if properties["original_source"] else "mesh_edit"
    return "material" if item.operator == "scenario.apply_saved_material" else "import"


def test_native_result_applications_have_matching_mcp_purposes():
    schema = ast.literal_eval(_mcp_spec("prepare_result_application")[1])
    items = sja.describe(view(APPLICATION_ACTIONS, "applied", ASSETS), CONTEXT, TYPES)
    native = {_mcp_purpose(item) for item in items if item.group == "apply"}
    # Agents can prepare every application a native surface offers.
    assert native == {"import", "world", "restore_world", "material", "mesh_edit", "mesh_source"}
    assert native <= set(schema["purpose"]["enum"])


def test_core_descriptor_source_stays_free_of_blender():
    tree = ast.parse((ROOT / "scenario/core/ui/saved_job_actions.py").read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add((node.module or "").split(".")[0])
    assert modules == {"collections", "dataclasses"}


def test_mcp_only_first_frame_handoff_draws_no_native_control_or_reuse_row():
    assets = (("still", "image/png"),)
    alone = sja.describe(view(("use_first_frame",), "applied", assets), CONTEXT, TYPES)
    assert alone == ()
    ready = sja.describe(
        view(("import_images", "use_first_frame"), "ready", assets), CONTEXT, TYPES
    )
    assert [item.key for item in ready] == ["import_images", "awaiting_review"]
    applied = sja.describe(
        view(("import_images", "use_first_frame"), "applied", assets), CONTEXT, TYPES
    )
    assert [item.key for item in applied] == ["reuse", "import_images"]
    assert sja.MCP_ONLY == {"use_first_frame"}
    # Agents prepare it through the shared application tool.
    schema = ast.literal_eval(_mcp_spec("prepare_result_application")[1])
    assert "video_first_frame" in schema["purpose"]["enum"]
    description, _ = _mcp_spec("job_status")
    assert "use_first_frame offers" in description
