# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved-job action descriptors shared by native result surfaces, without Blender."""

import ast
import itertools
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.core.jobs.playback import PLAYBACK_TYPES
from scenario.core.scene.panorama import WORLD_MEDIA_TYPES
from scenario.core.ui import saved_job_actions as sja

ROOT = Path(__file__).resolve().parents[2]
TYPES = sja.ResultTypes(
    media={"video/mp4": "video", "video/webm": "video", "audio/wav": "audio"},
    world=WORLD_MEDIA_TYPES,
)
PLAYABLE = sja.ResultTypes(
    media=TYPES.media,
    world=TYPES.world,
    playback={media_type: kind for media_type, (kind, _) in PLAYBACK_TYPES.items()},
)
CONTEXT = "context-token"
JOB = (("context_id", CONTEXT), ("request_id", "request"), ("expected_revision", 7))


def view(actions=(), state="remote", assets=(), **meta):
    # ModelJobs projects import units from the manifest; GLBs stand in here.
    glbs = [asset_id for asset_id, media_type in assets if media_type == "model/gltf-binary"]
    units = tuple((asset_id, "glb", index == 0) for index, asset_id in enumerate(glbs))
    return SimpleNamespace(
        local_id="request",
        asset_ids=[asset_id for asset_id, _ in assets],
        asset_types=dict(assets),
        meta={
            "shared_job": True,
            "saved_revision": 7,
            "saved_state": state,
            "recovery_actions": tuple(actions),
            "import_units": units,
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
    "use_first_frame",
)
VOCABULARY = (*sja.RECOVERY_ACTIONS, *APPLICATION_ACTIONS, "recover_blockout")
ASSETS = (
    ("clip", "video/webm"),
    ("panorama", "image/exr"),
    ("mesh", "model/gltf-binary"),
    ("still", "image/png"),
)
# ModelJobs projects World candidates as world_assets.
WORLD = {"world_assets": ("panorama",)}
# ModelJobs projects the stills a first-frame review accepts.
FIRST_FRAME = {"first_frame_assets": ("still",)}
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


def test_waiting_workflow_step_is_a_status_row_before_the_recovery_controls():
    items = sja.describe(view(("review_step", "refresh", "resume")), CONTEXT, TYPES)
    assert rows(items) == [
        ("review_step", "status", None, "Workflow waits for your decision", "INFO", {}),
        recover("refresh", "recover"),
        recover("resume", "recover"),
    ]
    # The row keeps the ModelJobs and MCP action name but grants no control.
    assert items[0].action == "review_step" and items[0].operator is None


def step(node_id="check", node_type="user-approval", **fields):
    values = {
        "node_id": node_id,
        "node_type": node_type,
        "iteration_index": None,
        "items": (),
        "minimum": None,
        "maximum": None,
        "actions": ("approve", "reject"),
        "blocked": "",
        "review_id": f"review-{node_id}",
        **fields,
    }
    return SimpleNamespace(**values)


def workflow_view(actions=("review_step", "refresh", "resume"), state="remote", **meta):
    subject = view(actions, state, **meta)
    subject.kind = "workflow"
    return subject


def review(label, node_id):
    return (
        f"review_step:{label}",
        "decide",
        "scenario.review_workflow_step",
        None,
        "NONE",
        dict(JOB, node_id=node_id, review_id=f"review-{node_id}"),
    )


WAITING = ("review_step", "status", None, "Workflow waits for your decision", "INFO", {})
RUNNING = [
    ("workflow_running", "status", None, "Scenario cannot cancel a running", "INFO", {}),
    ("workflow_running:1", "status", None, "workflow step; it finishes or pauses", "NONE", {}),
    ("workflow_running:2", "status", None, "at its next approval or selection.", "NONE", {}),
]


def test_each_waiting_step_gets_a_review_control_with_its_binding():
    selection = step(
        "pick",
        "user-selection",
        items=("a", "b", "c"),
        minimum=1,
        maximum=2,
        actions=("select", "reject"),
        iteration_index=0,
    )
    exact = step(
        "one",
        "user-selection",
        items=("a", "b"),
        minimum=1,
        maximum=1,
        actions=("select", "reject"),
    )
    blocked = step(
        "loop",
        "user-selection",
        items=("a",),
        minimum=1,
        maximum=1,
        actions=("reject",),
        blocked="loop",
    )
    unsendable = step("bad id ", actions=(), blocked="unidentified")
    steps = sja.WorkflowSteps(7, (step(), selection, exact, blocked, unsendable))
    items = sja.describe(workflow_view(), CONTEXT, TYPES, workflow_steps=steps)
    expected = [
        WAITING,
        review(0, "check"),
        review(1, "pick"),
        review(2, "one"),
        review(3, "loop"),
        ("review_step:4", "status", None, "This step cannot be decided here", "ERROR", {}),
        recover("refresh", "recover"),
        recover("resume", "recover"),
    ]
    labels = {
        1: "Review approval",
        2: "Choose 1 to 2 of 3 (loop index 0)",
        3: "Choose 1 of 2",
        4: "Review blocked selection",
    }
    for index, label in labels.items():
        expected[index] = expected[index][:3] + (label,) + expected[index][4:]
    assert rows(items) == expected
    # No cancellation notice while a step waits: rejecting it is the way to stop.
    assert not any(item.key.startswith("workflow_running") for item in items)


def test_steps_projected_for_another_revision_offer_no_control():
    stale = sja.WorkflowSteps(6, (step(),))
    items = sja.describe(workflow_view(), CONTEXT, TYPES, workflow_steps=stale)
    assert rows(items) == [WAITING, recover("refresh", "recover"), recover("resume", "recover")]
    # Without the owner's projection the status row stays, without controls.
    assert rows(sja.describe(workflow_view(), CONTEXT, TYPES))[0] == WAITING


def test_running_workflow_without_waiting_step_explains_that_it_cannot_be_canceled():
    plain = workflow_view(("refresh", "resume"))
    items = sja.describe(plain, CONTEXT, TYPES, workflow_steps=sja.WorkflowSteps())
    assert rows(items) == [recover("refresh", "recover"), recover("resume", "recover"), *RUNNING]
    assert all(item.operator is None for item in items if item.key.startswith("workflow_running"))
    # The owner is not needed for the notice, and a refresh in flight keeps it.
    assert rows(sja.describe(workflow_view(()), CONTEXT, TYPES)) == RUNNING
    # A refresh in flight hides the controls but a projected step still waits.
    waiting = sja.WorkflowSteps(7, (step(),))
    assert sja.describe(workflow_view(()), CONTEXT, TYPES, workflow_steps=waiting) == ()
    # Model jobs, and workflow jobs no longer running, never show it.
    model = view(("refresh", "resume", "cancel"))
    model.kind = "model"
    assert "workflow_running" not in {item.key for item in sja.describe(model, CONTEXT, TYPES)}
    for state in ("succeeded", "ready", "canceled", "prepared"):
        finished = workflow_view((), state)
        keys = {item.key for item in sja.describe(finished, CONTEXT, TYPES)}
        assert not any(key.startswith("workflow_running") for key in keys), state


def test_a_decision_in_flight_and_its_error_are_status_rows():
    sending = sja.WorkflowSteps(7, (step(),), deciding=True)
    items = sja.describe(workflow_view(()), CONTEXT, TYPES, workflow_steps=sending)
    assert rows(items) == [
        ("decision_sending", "status", None, "Sending your decision...", "TIME", {}),
    ]
    error = (
        "Decision outcome unknown; refresh the job and do not repeat the decision until the "
        "step is shown again"
    )
    failed = sja.WorkflowSteps(7, (), error=error)
    items = sja.describe(
        workflow_view(("refresh", "resume")), CONTEXT, TYPES, workflow_steps=failed
    )
    errors = [item for item in items if item.key.startswith("decision_error")]
    # The whole message is drawn, wrapped, never clipped to one line.
    assert " ".join(item.label for item in errors) == error
    assert [item.icon for item in errors] == ["ERROR"] + ["NONE"] * (len(errors) - 1)
    assert all(len(item.label) <= sja.NOTE_WIDTH and item.action == "" for item in errors)
    assert {item.key.partition(":")[0] for item in errors} <= sja.DECISION_ROWS
    # Other jobs never draw a workflow decision row.
    model = view(("refresh",))
    model.kind = "model"
    assert sja.describe(model, CONTEXT, TYPES, workflow_steps=failed) == sja.describe(
        model, CONTEXT, TYPES
    )


def test_review_labels_name_what_the_step_asks_for():
    assert sja.step_label(step()) == "Review approval"
    assert sja.step_label(step(iteration_index=3)) == "Review approval (loop index 3)"
    many = step("pick", "user-selection", items=("a",) * 5, minimum=2, maximum=100)
    assert sja.step_label(many) == "Choose 2 to 5 of 5"
    unreadable = step("pick", "user-selection", blocked="unsupported", actions=("reject",))
    assert sja.step_label(unreadable) == "Review blocked selection"


def test_ready_images_offer_import_world_and_material_then_await_review():
    assets = (
        ("first", "image/png"),
        ("depth", "image/webp"),
        ("second", "image/jpeg"),
        ("third", "image/x-exr"),
    )
    actions = ("import_images", "apply_world", "apply_material")
    candidates = ("first", "second", "third")
    items = sja.describe(view(actions, "ready", assets, world_assets=candidates), CONTEXT, TYPES)
    world = "scenario.apply_saved_world"
    assert rows(items) == [
        ("import_images", "apply", "scenario.import_saved_images", "Import saved images", "NONE", dict(JOB)),
        # World numbering counts every saved asset, as the per-asset imports do.
        asset("apply_world", world, "Set panorama as World (1)", "first", purpose="world"),
        asset("apply_world", world, "Set panorama as World (3)", "second", purpose="world"),
        asset("apply_world", world, "Set panorama as World (4)", "third", purpose="world"),
        ("apply_material", "apply", "scenario.apply_saved_material", "Apply saved material", "NONE", dict(JOB)),
        AWAITING,
    ]  # fmt: skip


def test_world_offers_only_projected_candidates_of_an_accepted_media_type():
    # A 3D package: its PBR maps share PNG with panoramas but are not projected.
    assets = (
        ("mesh", "model/gltf-binary"),
        ("albedo", "image/png"),
        ("panorama", "image/png"),
        ("normal", "image/png"),
        ("depth", "image/webp"),
    )
    subject = view(("apply_world",), "ready", assets, world_assets=("panorama", "depth"))
    items = sja.describe(subject, CONTEXT, TYPES)
    world = "scenario.apply_saved_world"
    assert rows(items) == [
        asset("apply_world", world, "Set panorama as World (3)", "panorama", purpose="world"),
        AWAITING,
    ]
    # Without a projected candidate list, nothing is offered as a World.
    unprojected = view(("apply_world",), "ready", assets)
    assert [item.key for item in sja.describe(unprojected, CONTEXT, TYPES)] == ["awaiting_review"]


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
        asset("import_model", model, "Import GLB model (4)", "mesh"),
        asset("import_model", model, "Import alternate: GLB (6)", "variant"),
        asset("apply_mesh", mesh, "Apply mesh edit (4)", "mesh", original_source=False),
        # In place, an alternate GLB is named as its import is.
        asset(
            "apply_mesh",
            mesh,
            "Apply alternate mesh edit: GLB (6)",
            "variant",
            original_source=False,
        ),
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
            "Apply alternate to captured source: GLB (6)",
            "variant",
            original_source=True,
        ),
        AWAITING,
    ]
    # In-place edits stage a classified unit; an unclassified GLB offers none.
    unclassified = view(("apply_mesh",), "apply_failed", assets, import_units=())
    assert [item.key for item in sja.describe(unclassified, CONTEXT, TYPES)] == ["awaiting_review"]


def test_mesh_edits_name_fbx_obj_and_gltf_units_and_skip_splats_and_ply():
    # A UV job: FBX first, two OBJ alternates, maps; then other formats.
    assets = (
        ("albedo", "image/png"),
        ("fbx", "model/x-fbx"),
        ("obj-a", "model/obj"),
        ("obj-b", "model/obj"),
        ("gltf", "model/gltf+json"),
        ("ply", "model/ply"),
        ("spz", "model/spz"),
    )
    units = (
        ("fbx", "fbx", True),
        ("gltf", "gltf", False),
        ("obj-a", "obj", False),
        ("obj-b", "obj", False),
        ("ply", "ply", False),
        ("spz", "spz", False),
    )
    actions = ("apply_mesh", "apply_mesh_source")
    subject = view(actions, "ready", assets, import_units=units)
    mesh = "scenario.apply_saved_mesh"
    edit = {"original_source": False}
    source = {"original_source": True}
    assert rows(sja.describe(subject, CONTEXT, TYPES)) == [
        asset("apply_mesh", mesh, "Apply mesh edit: FBX (2)", "fbx", **edit),
        asset("apply_mesh", mesh, "Apply alternate mesh edit: glTF (5)", "gltf", **edit),
        asset("apply_mesh", mesh, "Apply alternate mesh edit: OBJ (3)", "obj-a", **edit),
        asset("apply_mesh", mesh, "Apply alternate mesh edit: OBJ (4)", "obj-b", **edit),
        asset("apply_mesh_source", mesh, "Apply to captured source: FBX (2)", "fbx", **source),
        asset(
            "apply_mesh_source",
            mesh,
            "Apply alternate to captured source: glTF (5)",
            "gltf",
            **source,
        ),
        asset(
            "apply_mesh_source",
            mesh,
            "Apply alternate to captured source: OBJ (3)",
            "obj-a",
            **source,
        ),
        asset(
            "apply_mesh_source",
            mesh,
            "Apply alternate to captured source: OBJ (4)",
            "obj-b",
            **source,
        ),
        AWAITING,
    ]
    # A primary GLB keeps the plain wording beside an alternate OBJ.
    remesh = view(
        ("apply_mesh",),
        "ready",
        (("glb", "model/gltf-binary"), ("obj", "model/obj")),
        import_units=(("glb", "glb", True), ("obj", "obj", False)),
    )
    assert [item.label for item in sja.describe(remesh, CONTEXT, TYPES)][:2] == [
        "Apply mesh edit (1)",
        "Apply alternate mesh edit: OBJ (2)",
    ]


def test_model_imports_follow_the_projected_units_in_classified_order():
    assets = (
        ("texture", "image/png"),
        ("material", "model/mtl"),
        ("obj", "model/obj"),
        ("fbx", "application/vnd.autodesk.fbx"),
        ("gltf", "model/gltf+json"),
        ("ply", "model/ply"),
        ("glb", "model/glb"),
        ("spz", "model/spz"),
        ("splat", "model/splat"),
        ("sog", "model/sog"),
    )
    units = (
        ("glb", "glb", True),
        ("gltf", "gltf", False),
        ("fbx", "fbx", False),
        ("obj", "obj", False),
        ("ply", "ply", False),
        ("spz", "spz", False),
        ("splat", "splat", False),
        # Unknown formats or keys never become controls.
        ("sog", "sog", False),
        ("missing", "obj", False),
    )
    subject = view(("import_model",), "ready", assets, import_units=units)
    model = "scenario.import_saved_model"
    assert rows(sja.describe(subject, CONTEXT, TYPES)) == [
        asset("import_model", model, "Import GLB model (7)", "glb"),
        asset("import_model", model, "Import alternate: glTF (5)", "gltf"),
        asset("import_model", model, "Import alternate: FBX (4)", "fbx"),
        asset("import_model", model, "Import alternate: OBJ (3)", "obj"),
        asset("import_model", model, "Import alternate: PLY (6)", "ply"),
        asset("import_model", model, "Import alternate splats: SPZ (8)", "spz"),
        asset("import_model", model, "Import alternate splats: .splat (9)", "splat"),
        AWAITING,
    ]
    # Another unit is primary when this release cannot import the first one.
    alternates = view(("import_model",), "ready", assets, import_units=units[1:2])
    assert [item.label for item in sja.describe(alternates, CONTEXT, TYPES)][:1] == [
        "Import alternate: glTF (5)"
    ]
    splats = view(("import_model",), "ready", assets, import_units=(("spz", "spz", True),))
    assert [item.label for item in sja.describe(splats, CONTEXT, TYPES)][:1] == [
        "Import splats: SPZ (8)"
    ]
    assert sja.describe(view(("import_model",), "applied", assets), CONTEXT, TYPES)[1:] == ()


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
            items = sja.describe(
                view(actions, state, ASSETS, **WORLD, **FIRST_FRAME), CONTEXT, TYPES
            )
            keys = [item.key for item in items]
            assert len(keys) == len(set(keys)), actions
            offered = {item.action for item in items if item.operator is not None}
            assert offered == set(actions), actions
            for item in items:
                assert item.group in {
                    "recover",
                    "cancel",
                    "apply",
                    "receipt",
                    "decide",
                    "prefill",
                    "status",
                }
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
    assert {TYPES: True}[TYPES] and TYPES != sja.ResultTypes({}, frozenset())


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
    control = [
        action
        for action in sja.RECOVERY_ACTIONS
        if action != "cancel_prepared" and action not in sja.NATIVE_ONLY
    ]
    assert schema["action"]["enum"] == control
    # Marking an unconfirmed request reviewed stays the user's decision in Blender.
    assert sja.NATIVE_ONLY == {"mark_reviewed"}
    assert not sja.NATIVE_ONLY & set(schema["action"]["enum"])
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
    if item.operator == sja.FIRST_FRAME_OPERATOR:
        return "video_first_frame"
    if item.operator == "scenario.apply_saved_mesh":
        return "mesh_source" if properties["original_source"] else "mesh_edit"
    return "material" if item.operator == "scenario.apply_saved_material" else "import"


def test_native_result_applications_have_matching_mcp_purposes():
    schema = ast.literal_eval(_mcp_spec("prepare_result_application")[1])
    items = sja.describe(
        view(APPLICATION_ACTIONS, "applied", ASSETS, **WORLD, **FIRST_FRAME), CONTEXT, TYPES
    )
    native = {_mcp_purpose(item) for item in items if item.group == "apply"}
    # Agents can prepare every application a native surface offers.
    assert native == {
        "import",
        "world",
        "restore_world",
        "material",
        "mesh_edit",
        "mesh_source",
        "video_first_frame",
    }
    assert native <= set(schema["purpose"]["enum"])


def test_core_descriptor_source_stays_free_of_blender():
    tree = ast.parse((ROOT / "scenario/core/ui/saved_job_actions.py").read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add((node.module or "").split(".")[0])
    assert modules == {"collections", "dataclasses", "textwrap"}


def test_first_frame_controls_follow_the_projected_stills_and_number_every_asset():
    assets = (
        ("clip", "video/mp4"),
        ("colour", "image/png"),
        ("normal", "image/png"),
        ("base", "image/webp"),
    )
    accepted = {"first_frame_assets": ("colour", "base")}
    first_frame = sja.FIRST_FRAME_OPERATOR
    ready = sja.describe(view(("use_first_frame",), "ready", assets, **accepted), CONTEXT, TYPES)
    assert rows(ready) == [
        asset("use_first_frame", first_frame, "Use as video first frame (2)", "colour"),
        asset("use_first_frame", first_frame, "Use as video first frame (4)", "base"),
        AWAITING,
    ]
    assert first_frame == "scenario.use_saved_first_frame"
    # The media type alone never offers a still: a normal map is a PNG too.
    unprojected = sja.describe(view(("use_first_frame",), "ready", assets), CONTEXT, TYPES)
    assert rows(unprojected) == [AWAITING]
    # On a completed job it is a reuse action like any other saved application.
    applied = sja.describe(
        view(("import_images", "use_first_frame"), "applied", assets, **accepted), CONTEXT, TYPES
    )
    assert [item.key for item in applied] == [
        "reuse",
        "import_images",
        "use_first_frame:colour",
        "use_first_frame:base",
    ]
    # Agents prepare the same review through the shared application tool.
    schema = ast.literal_eval(_mcp_spec("prepare_result_application")[1])
    assert "video_first_frame" in schema["purpose"]["enum"]
    description, _ = _mcp_spec("job_status")
    assert "use_first_frame offers" in description


def test_session_import_notices_are_status_rows_after_the_controls():
    notices = ("Shown as points: 12 of 40 splats", "This SPZ declares extensions; check its axes")
    subject = view(
        ("import_model",),
        "applied",
        (("spz", "model/spz"),),
        import_units=(("spz", "spz", True),),
        import_notices=notices,
    )
    items = sja.describe(subject, CONTEXT, TYPES)
    assert [(item.key, item.group, item.operator, item.label, item.icon) for item in items] == [
        ("reuse", "status", None, "Reuse saved results", "FILE_REFRESH"),
        (
            "import_model:spz",
            "apply",
            "scenario.import_saved_model",
            "Import splats: SPZ (1)",
            "NONE",
        ),
        ("import_notice:0", "status", None, notices[0], "INFO"),
        ("import_notice:1", "status", None, notices[1], "INFO"),
    ]


def prefill(asset_id, index):
    return (
        f"make_hdri:{asset_id}",
        "prefill",
        sja.HDRI_OPERATOR,
        f"Make HDRI ({index})",
        "NONE",
        dict(JOB, asset_id=asset_id),
    )


def test_saved_360_results_are_labelled_and_ldr_ones_prefill_make_hdri():
    panoramas = {"flat": "ldr", "exr": "hdr", "second": "ldr"}
    subject = view(
        ("apply_world",),
        "ready",
        (
            ("flat", "image/png"),
            ("exr", "image/aces"),
            ("plain", "image/png"),
            ("second", "image/jpeg"),
        ),
        panoramas=panoramas,
        panorama_inputs=("flat", "second"),
        world_assets=("flat", "exr", "plain", "second"),
    )
    items = rows(sja.describe(subject, CONTEXT, TYPES))
    world = [item for item in items if item[0].startswith("apply_world")]
    assert items[0] == ("panorama", "status", None, "360 panorama and HDR environment", "WORLD", {})
    # The World candidates keep their own label and numbering.
    assert [item[3] for item in world] == [f"Set panorama as World ({n})" for n in range(1, 5)]
    assert items[len(world) + 1 :] == [
        prefill("flat", 1),
        prefill("second", 2),
        (
            "awaiting_review",
            "status",
            None,
            "Downloaded result awaits application review",
            "INFO",
            {},
        ),
    ]


def play(asset_id, index, kind, playing=False):
    if kind == "video":
        return [
            (
                f"play:{asset_id}",
                "playback",
                "scenario.play_saved_media",
                f"Play video ({index})",
                "NONE",
                dict(JOB, asset_id=asset_id, player="SYSTEM"),
            ),
            (
                f"play_in_blender:{asset_id}",
                "playback",
                "scenario.play_saved_media",
                f"Play in Blender ({index})",
                "NONE",
                dict(JOB, asset_id=asset_id, player="BLENDER"),
            ),
        ]
    if playing:
        stop = dict(JOB, asset_id=asset_id)
        del stop["expected_revision"]
        toggle = (
            f"stop_audio:{asset_id}",
            "playback",
            "scenario.stop_saved_audio",
            f"Stop audio ({index})",
            "NONE",
            stop,
        )
    else:
        toggle = (
            f"play:{asset_id}",
            "playback",
            "scenario.play_saved_audio",
            f"Play audio ({index})",
            "NONE",
            dict(JOB, asset_id=asset_id),
        )
    return [
        toggle,
        (
            f"waveform:{asset_id}",
            "playback",
            "scenario.preview_saved_waveform",
            f"Waveform ({index})",
            "NONE",
            dict(JOB, asset_id=asset_id),
        ),
        (
            f"system_player:{asset_id}",
            "playback",
            "scenario.play_saved_media",
            f"Open in system player ({index})",
            "NONE",
            dict(JOB, asset_id=asset_id, player="SYSTEM"),
        ),
    ]


def test_downloaded_media_offer_players_waveform_and_the_system_player_in_rows():
    assets = (
        ("clip", "video/mp4"),
        ("texture", "image/png"),
        ("sound", "audio/wav"),
        ("mesh", "model/gltf-binary"),
        ("stem", "audio/flac"),
    )
    items = sja.describe(view(("import_media",), "ready", assets), CONTEXT, PLAYABLE)
    media = "scenario.import_saved_media"
    assert rows(items) == [
        asset("import_media", media, "Add video strip (1)", "clip"),
        asset("import_media", media, "Add audio strip (3)", "sound"),
        *play("clip", 1, "video"),
        *play("sound", 3, "audio"),
        *play("stem", 5, "audio"),
        AWAITING,
    ]
    playback = [item for item in items if item.group == "playback"]
    # Video: one row. Audio: Play audio and Waveform, then the system player.
    assert [item.row for item in playback] == [
        "playback:clip",
        "playback:clip",
        "playback:sound",
        "playback:sound",
        "system:sound",
        "playback:stem",
        "playback:stem",
        "system:stem",
    ]
    assert all(not item.row for item in items if item.group != "playback")
    # Not job actions: MCP job_status never reports them.
    assert {item.action for item in playback} == {
        "play",
        "play_in_blender",
        "waveform",
        "system_player",
    }
    assert not {item.action for item in playback} & set(VOCABULARY)


def test_the_playing_audio_result_offers_stop_and_the_others_play():
    assets = (("clip", "video/mp4"), ("sound", "audio/wav"), ("stem", "audio/flac"))
    subject = view((), "ready", assets)
    items = sja.describe(subject, CONTEXT, PLAYABLE, listening="stem")
    assert rows(items) == [
        *play("clip", 1, "video"),
        *play("sound", 2, "audio"),
        *play("stem", 3, "audio", playing=True),
        AWAITING,
    ]
    assert "stop_audio" not in VOCABULARY
    # A video or another job's asset never turns into Stop.
    for listening in ("clip", "absent", None):
        described = sja.describe(subject, CONTEXT, PLAYABLE, listening=listening)
        assert all(item.action != "stop_audio" for item in described)


@pytest.mark.parametrize("state", ["applying", "apply_failed", "applied"])
def test_playback_stays_available_for_interrupted_and_applied_results(state):
    items = sja.describe(view((), state, (("clip", "video/webm"),)), CONTEXT, PLAYABLE)
    assert [item.key for item in items if item.group == "playback"] == [
        "play:clip",
        "play_in_blender:clip",
    ]


@pytest.mark.parametrize(
    ("kinds", "label"),
    [
        ({"a": "ldr"}, "360 panorama (LDR)"),
        ({"a": "hdr"}, "360 HDR environment (OpenEXR)"),
        ({"a": "ldr", "b": "hdr"}, "360 panorama and HDR environment"),
    ],
)
def test_panorama_label_never_calls_an_ldr_result_hdr(kinds, label):
    items = sja.describe(view((), "applied", panoramas=kinds), CONTEXT, TYPES)
    assert [(item.key, item.label) for item in items] == [("panorama", label)]


@pytest.mark.parametrize("state", ["remote", "downloading", "applying", "download_failed"])
def test_make_hdri_waits_for_a_settled_downloaded_result(state):
    subject = view((), state, panoramas={"flat": "ldr"}, panorama_inputs=("flat",))
    items = sja.describe(subject, CONTEXT, TYPES)
    assert [item.key for item in items] == ["panorama"]


@pytest.mark.parametrize("state", sorted(sja.PREFILL_STATES))
def test_make_hdri_is_offered_on_settled_states_and_absent_without_ldr_inputs(state):
    with_input = sja.describe(
        view((), state, panoramas={"flat": "ldr"}, panorama_inputs=("flat",)), CONTEXT, TYPES
    )
    assert [item.key for item in with_input if item.group == "prefill"] == ["make_hdri:flat"]
    hdr_only = sja.describe(view((), state, panoramas={"exr": "hdr"}), CONTEXT, TYPES)
    assert all(item.group != "prefill" for item in hdr_only)


def test_views_without_projection_keep_their_previous_descriptors():
    plain = view(("import_images",), "ready", (("image", "image/png"),))
    assert [item.key for item in sja.describe(plain, CONTEXT, TYPES)] == [
        "import_images",
        "awaiting_review",
    ]


@pytest.mark.parametrize(
    "state", ["prepared", "remote", "succeeded", "downloading", "download_failed", "canceled"]
)
def test_results_that_are_not_saved_locally_offer_no_playback(state):
    items = sja.describe(view(("resume",), state, (("clip", "video/mp4"),)), CONTEXT, PLAYABLE)
    assert [item for item in items if item.group == "playback"] == []


def test_playback_needs_owner_media_types_and_a_shared_projection():
    assets = (("clip", "video/mp4"), ("sound", "audio/wav"))
    assert [item.group for item in sja.describe(view((), "ready", assets), CONTEXT, TYPES)] == [
        "status"
    ]
    assert sja.describe(view((), "ready", assets, shared_job=False), CONTEXT, PLAYABLE) == ()
    unrevised = view((), "ready", assets)
    del unrevised.meta["saved_revision"]
    assert sja.describe(unrevised, CONTEXT, PLAYABLE) == ()
