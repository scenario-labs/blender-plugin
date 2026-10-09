# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved 3D result package classification over synthetic manifests."""

import random
import struct

import pytest

from scenario.core.jobs.store import ResultAsset, StoredResult
from scenario.core.jobs.transfers import DownloadedResult
from scenario.core.scene import model_formats as mf
from scenario.core.scene.model_formats import (
    MAX_MEMBER_BYTES,
    ModelFormat,
    ModelPackageError,
    PackageMember,
    UnitKind,
    check_signature,
    classify_packages,
    inspect_ply_header,
    members_from_results,
)

MiB = 1024 * 1024


def member(asset_id, media, size=1000, role=None, kind=None, parent=None):
    return PackageMember(asset_id, media, size, role, kind, parent)


def derived_obj_package_job():
    """GLB root output, derived OBJ child, MTL and maps under the OBJ."""
    return [
        member("asset_glb", "model/gltf-binary", kind="txt23d", parent="asset_input"),
        member("asset_obj", "model/obj", kind="txt23d", parent="asset_glb"),
        member("asset_mtl", "model/mtl", kind="3d-texture-mtl", parent="asset_obj"),
        member(
            "asset_alb", "image/png", role="albedo", kind="3d-texture-albedo", parent="asset_obj"
        ),
        member(
            "asset_nrm", "image/png", role="normal", kind="3d-texture-normal", parent="asset_obj"
        ),
        member(
            "asset_rgh",
            "image/jpeg",
            role="roughness",
            kind="3d-texture-roughness",
            parent="asset_obj",
        ),
        member(
            "asset_met",
            "image/png",
            role="metallic",
            kind="3d-texture-metallic",
            parent="asset_obj",
        ),
    ]


@pytest.mark.parametrize(
    ("media", "fmt"),
    [
        ("model/gltf-binary", ModelFormat.GLB),
        ("model/glb", ModelFormat.GLB),
        ("model/gltf+json", ModelFormat.GLTF),
        ("model/x-fbx", ModelFormat.FBX),
        ("application/vnd.autodesk.fbx", ModelFormat.FBX),
        ("application/x.autodesk.fbx", ModelFormat.FBX),
        ("model/obj", ModelFormat.OBJ),
        ("model/ply", ModelFormat.PLY),
        ("application/x-ply", ModelFormat.PLY),
        ("model/spz", ModelFormat.SPZ),
        ("model/splat", ModelFormat.SPLAT),
    ],
)
def test_every_mime_alias_selects_one_format(media, fmt):
    assert mf.model_format(media) is fmt
    assert not mf.unsupported_model(media)


@pytest.mark.parametrize(
    "media",
    [
        "model/ksplat",
        "model/sog",
        "model/stl",
        "model/usd",
        "model/x-3d-vox",
        "model/vnd.collada+xml",
        "model/x3d+xml",
        "model/x-maya-binary",
    ],
)
def test_unsupported_model_formats_are_reported_not_imported(media):
    assert mf.model_format(media) is None and mf.unsupported_model(media)
    plan = classify_packages([member("asset_a", media), member("asset_b", "model/spz")])
    assert [unit.key for unit in plan.units] == ["asset_b"]
    assert plan.findings == (mf.Finding("asset_a", mf.UNSUPPORTED_FORMAT),)


def test_companions_and_images_are_not_formats_or_unsupported_models():
    for media in ("model/mtl", "image/png", "application/octet-stream", None):
        assert mf.model_format(media) is None and not mf.unsupported_model(media)


def test_lineage_binds_obj_material_and_maps_and_puts_the_root_output_first():
    plan = classify_packages(derived_obj_package_job())
    assert plan.lineage
    glb, obj = plan.units
    assert (glb.key, glb.primary, glb.main, glb.format, glb.kind) == (
        "asset_glb",
        True,
        True,
        ModelFormat.GLB,
        UnitKind.MESH,
    )
    assert glb.files == (("asset_glb", "model.glb"),) and glb.binding == mf.BINDING_SINGLE
    assert (obj.primary, obj.main, obj.binding, obj.material) == (
        False,
        False,
        mf.BINDING_PARENT,
        "asset_mtl",
    )
    assert obj.textures == (
        ("albedo", "asset_alb"),
        ("normal", "asset_nrm"),
        ("roughness", "asset_rgh"),
        ("metallic", "asset_met"),
    )
    assert obj.files == (
        ("asset_obj", "model.obj"),
        ("asset_mtl", "material.mtl"),
        ("asset_alb", "texture-albedo.png"),
        ("asset_nrm", "texture-normal.png"),
        ("asset_rgh", "texture-roughness.jpg"),
        ("asset_met", "texture-metallic.png"),
    )
    assert obj.members == tuple(asset_id for asset_id, _ in obj.files)
    assert plan.findings == () and plan.primary is glb and plan.unit("asset_obj") is obj
    assert plan.unit("asset_alb") is None


def test_parent_links_separate_several_obj_packages_in_one_job():
    members = []
    for name in ("a", "b"):
        members += [
            member(f"asset_obj_{name}", "model/obj", kind="txt23d", parent="asset_input"),
            member(
                f"asset_mtl_{name}", "model/mtl", kind="3d-texture-mtl", parent=f"asset_obj_{name}"
            ),
            member(
                f"asset_alb_{name}",
                "image/png",
                role="albedo",
                kind="3d-texture-albedo",
                # Maps may also hang from the material library.
                parent=f"asset_mtl_{name}" if name == "b" else f"asset_obj_{name}",
            ),
        ]
    plan = classify_packages(members)
    assert [(u.key, u.material, u.textures, u.main) for u in plan.units] == [
        ("asset_obj_a", "asset_mtl_a", (("albedo", "asset_alb_a"),), True),
        ("asset_obj_b", "asset_mtl_b", (("albedo", "asset_alb_b"),), True),
    ]
    assert plan.findings == ()


def test_ambiguous_maps_and_materials_stay_saved_and_are_reported():
    job = derived_obj_package_job() + [
        member("asset_alb2", "image/png", role="base", kind="texture", parent="asset_obj"),
        member("asset_ao", "image/png", role="ao", kind="texture-ao", parent="asset_obj"),
        member("asset_misc", "image/png", kind="3d23d-texture", parent="asset_obj"),
    ]
    obj = classify_packages(job).unit("asset_obj")
    assert [slot for slot, _ in obj.textures] == ["normal", "roughness", "metallic"]
    assert dict((f.asset_id, f.reason) for f in classify_packages(job).findings) == {
        "asset_alb": mf.AMBIGUOUS_TEXTURE,
        "asset_alb2": mf.AMBIGUOUS_TEXTURE,
        "asset_ao": mf.UNBOUND,
        "asset_misc": mf.UNBOUND,
    }
    job = derived_obj_package_job() + [
        member("asset_mtl2", "model/mtl", kind="3d-texture-mtl", parent="asset_obj")
    ]
    plan = classify_packages(job)
    obj = plan.unit("asset_obj")
    assert (
        obj.material is None and obj.textures == () and obj.files == (("asset_obj", "model.obj"),)
    )
    reasons = {f.asset_id: f.reason for f in plan.findings}
    assert reasons["asset_mtl"] == reasons["asset_mtl2"] == mf.AMBIGUOUS_MATERIAL
    assert reasons["asset_alb"] == mf.NO_MATERIAL


def test_a_model_child_of_the_material_is_its_own_unit_not_an_unbound_companion():
    job = derived_obj_package_job() + [
        member("asset_glb2", "model/glb", kind="3d23d", parent="asset_mtl")
    ]
    plan = classify_packages(job)
    assert [u.key for u in plan.units] == ["asset_glb", "asset_glb2", "asset_obj"]
    assert len(plan.unit("asset_obj").textures) == 4 and plan.findings == ()


def test_material_without_an_obj_parent_is_reported_unbound():
    plan = classify_packages(
        [
            member("asset_glb", "model/glb", kind="img23d"),
            member("asset_mtl", "model/mtl", kind="3d-texture-mtl", parent="asset_glb"),
        ]
    )
    assert [u.key for u in plan.units] == ["asset_glb"]
    assert plan.findings == (mf.Finding("asset_mtl", mf.UNBOUND),)


def test_lineage_reports_files_under_a_skipped_model_or_a_glb_as_unbound():
    job = derived_obj_package_job()
    job[1] = member("asset_obj", "model/obj", 300 * MiB, kind="txt23d", parent="asset_glb")
    job += [
        member("asset_obj2", "model/obj", kind="txt23d", parent="asset_glb"),
        member("asset_mtl_alb", "image/png", role="albedo", kind="texture", parent="asset_mtl"),
        member("asset_glb_alb", "image/png", role="albedo", kind="texture", parent="asset_glb"),
    ]
    plan = classify_packages(job)
    assert [u.key for u in plan.units] == ["asset_glb", "asset_obj2"]
    # With lineage a material is never ambiguous between packages; it is unbound.
    assert {f.asset_id: f.reason for f in plan.findings} == {
        "asset_obj": mf.TOO_LARGE,
        "asset_mtl": mf.UNBOUND,
        "asset_alb": mf.UNBOUND,
        "asset_nrm": mf.UNBOUND,
        "asset_rgh": mf.UNBOUND,
        "asset_met": mf.UNBOUND,
        "asset_mtl_alb": mf.UNBOUND,
        "asset_glb_alb": mf.UNBOUND,
    }


def legacy(members):
    return [
        PackageMember(m.asset_id, m.media_type, m.size, m.texture_role, None, None) for m in members
    ]


def test_legacy_manifest_binds_only_a_sole_obj_package():
    plan = classify_packages(legacy(derived_obj_package_job()))
    assert not plan.lineage
    glb, obj = plan.units
    assert glb.primary and not glb.main and not obj.main
    assert obj.binding == mf.BINDING_SOLE_PACKAGE and obj.material == "asset_mtl"
    assert len(obj.textures) == 4 and plan.findings == ()


def test_legacy_manifest_with_several_obj_files_binds_nothing():
    job = legacy(derived_obj_package_job()) + [member("asset_obj2", "model/obj")]
    plan = classify_packages(job)
    assert [(u.key, u.material, u.binding) for u in plan.units] == [
        ("asset_glb", None, mf.BINDING_SINGLE),
        ("asset_obj", None, mf.BINDING_SINGLE),
        ("asset_obj2", None, mf.BINDING_SINGLE),
    ]
    assert {f.reason for f in plan.findings} == {mf.AMBIGUOUS_PACKAGE}
    assert {f.asset_id for f in plan.findings} == {
        "asset_mtl",
        "asset_alb",
        "asset_nrm",
        "asset_rgh",
        "asset_met",
    }


def test_an_oversized_peer_still_prevents_sole_package_binding():
    plan = classify_packages(
        [
            member("asset_big", "model/obj", size=300 * MiB),
            member("asset_obj", "model/obj"),
            member("asset_mtl", "model/mtl"),
            member("asset_alb", "image/png", role="albedo"),
        ]
    )
    assert [(u.key, u.binding, u.material, u.textures) for u in plan.units] == [
        ("asset_obj", mf.BINDING_SINGLE, None, ())
    ]
    assert {f.asset_id: f.reason for f in plan.findings} == {
        "asset_big": mf.TOO_LARGE,
        "asset_mtl": mf.AMBIGUOUS_PACKAGE,
        "asset_alb": mf.AMBIGUOUS_PACKAGE,
    }
    plan = classify_packages(
        [
            member("asset_big", "model/gltf+json", size=8 * MiB + 1),
            member("asset_gltf", "model/gltf+json"),
            member("asset_bin", "application/octet-stream"),
        ]
    )
    assert (plan.primary.key, plan.primary.binding, plan.primary.resources) == (
        "asset_gltf",
        mf.BINDING_SINGLE,
        (),
    )


def test_partial_lineage_is_ignored_rather_than_mixed():
    job = derived_obj_package_job()
    job[3] = PackageMember("asset_alb", "image/png", 1000, "albedo", None, "asset_obj")
    plan = classify_packages(job)
    assert not plan.lineage and not plan.primary.main
    assert plan.unit("asset_obj").binding == mf.BINDING_SOLE_PACKAGE


def test_rank_orders_formats_then_manifest_and_marks_one_primary():
    job = [
        member("asset_splat", "model/splat"),
        member("asset_ply_unknown", "model/ply"),
        member("asset_spz", "model/spz"),
        member("asset_ply_mesh", "application/x-ply"),
        member("asset_obj", "model/obj"),
        member("asset_fbx2", "application/vnd.autodesk.fbx"),
        member("asset_fbx", "model/x-fbx"),
        member("asset_gltf", "model/gltf+json"),
        member("asset_glb", "model/glb"),
        member("asset_ply_splat", "model/ply"),
    ]
    plan = classify_packages(job, ply_kinds={"asset_ply_mesh": "mesh", "asset_ply_splat": "splat"})
    assert [u.key for u in plan.units] == [
        "asset_glb",
        "asset_gltf",
        "asset_fbx2",
        "asset_fbx",
        "asset_obj",
        "asset_ply_mesh",
        "asset_spz",
        "asset_ply_unknown",
        "asset_ply_splat",
        "asset_splat",
    ]
    assert [u.primary for u in plan.units] == [True] + [False] * 9
    kinds = {u.key: u.kind for u in plan.units}
    assert kinds["asset_ply_mesh"] is UnitKind.MESH
    assert kinds["asset_ply_splat"] is kinds["asset_spz"] is UnitKind.SPLAT
    assert kinds["asset_ply_unknown"] is UnitKind.PLY
    assert classify_packages(job, ply_kinds={"asset_ply_mesh": "mesh"}) == classify_packages(
        list(job), ply_kinds={"asset_ply_mesh": "mesh"}
    )


def test_ties_prefer_more_bound_companions_then_larger_files():
    job = [
        member("asset_obj_a", "model/obj", kind="txt23d", parent="asset_input"),
        member("asset_obj_b", "model/obj", kind="txt23d", parent="asset_input"),
        member("asset_mtl_b", "model/mtl", kind="3d-texture-mtl", parent="asset_obj_b"),
    ]
    assert [u.key for u in classify_packages(job).units] == ["asset_obj_b", "asset_obj_a"]
    job = [
        member("asset_unknown", "model/x-fbx", size=None),
        member("asset_small", "model/x-fbx", size=10),
        member("asset_large", "model/x-fbx", size=20),
        member("asset_twin", "model/x-fbx", size=20),
    ]
    assert [u.key for u in classify_packages(job).units] == [
        "asset_large",
        "asset_twin",
        "asset_small",
        "asset_unknown",
    ]


def test_generated_root_output_precedes_a_better_ranked_derived_format():
    plan = classify_packages(
        [
            member("asset_glb", "model/gltf-binary", kind="img23d", parent="asset_fbx"),
            member("asset_fbx", "model/x-fbx", kind="img23d", parent="asset_input"),
            member("asset_splat", "model/spz", kind="img2splat"),
        ]
    )
    assert [(u.key, u.main) for u in plan.units] == [
        ("asset_fbx", True),
        ("asset_splat", True),
        ("asset_glb", False),
    ]


def test_non_generation_types_are_never_main():
    plan = classify_packages([member("asset_up", "model/obj", kind="uploaded-3d")])
    assert not plan.primary.main and plan.primary.primary


@pytest.mark.parametrize(
    "kinds",
    [{"asset_obj": "mesh"}, {"asset_ply": "points"}, {"asset_missing": "splat"}],
)
def test_ply_kinds_apply_only_to_saved_ply_members(kinds):
    job = [member("asset_obj", "model/obj"), member("asset_ply", "model/ply")]
    with pytest.raises(ValueError):
        classify_packages(job, ply_kinds=kinds)


def test_size_bounds_reject_files_and_packages_before_import():
    plan = classify_packages(
        [
            member("asset_big", "model/glb", size=MAX_MEMBER_BYTES + 1),
            member("asset_gltf", "model/gltf+json", size=8 * MiB + 1),
            member("asset_fbx", "model/x-fbx", size=MAX_MEMBER_BYTES),
        ]
    )
    assert [u.key for u in plan.units] == ["asset_fbx"]
    assert plan.findings == (
        mf.Finding("asset_big", mf.TOO_LARGE),
        mf.Finding("asset_gltf", mf.TOO_LARGE),
    )
    job = derived_obj_package_job()
    job[2] = member(
        "asset_mtl", "model/mtl", 4 * MiB + 1, kind="3d-texture-mtl", parent="asset_obj"
    )
    plan = classify_packages(job)
    assert plan.unit("asset_obj").material is None
    assert {f.asset_id: f.reason for f in plan.findings}["asset_mtl"] == mf.TOO_LARGE
    job = derived_obj_package_job()
    job[1] = member("asset_obj", "model/obj", 200 * MiB, kind="txt23d", parent="asset_glb")
    job[3] = member("asset_alb", "image/png", 200 * MiB, "albedo", "3d-texture-albedo", "asset_obj")
    job[4] = member("asset_nrm", "image/png", 200 * MiB, "normal", "3d-texture-normal", "asset_obj")
    plan = classify_packages(job)
    assert [u.key for u in plan.units] == ["asset_glb"]
    assert [f.asset_id for f in plan.findings] == [m.asset_id for m in job[1:]]
    assert {f.reason for f in plan.findings} == {mf.PACKAGE_TOO_LARGE}


def test_image_only_jobs_have_no_units_or_findings():
    job = [member("asset_a", "image/png", role="albedo"), member("asset_b", "video/mp4")]
    plan = classify_packages(job)
    assert plan.units == () and plan.findings == () and plan.primary is None
    assert classify_packages([member(m.asset_id, m.media_type, kind="texture") for m in job]) == (
        mf.PackagePlan((), (), True)
    )


def test_gltf_resources_are_candidates_bound_later_by_reference():
    job = [
        member("asset_gltf", "model/gltf+json", kind="txt23d"),
        member("asset_bin", "application/octet-stream", kind="txt23d", parent="asset_gltf"),
        member("asset_tex", "image/png", kind="texture", parent="asset_gltf"),
        member("asset_other", "image/png", kind="texture", parent="asset_input"),
        member("asset_doc", "text/plain", kind="txt2txt", parent="asset_gltf"),
    ]
    plan = classify_packages(job)
    unit = plan.primary
    assert unit.binding == mf.BINDING_PARENT
    assert unit.resources == ("asset_bin", "asset_tex")
    assert unit.files == (("asset_gltf", "model.gltf"),)
    # Candidate resources are not findings; other files no unit lists are unbound.
    assert plan.findings == (
        mf.Finding("asset_other", mf.UNBOUND),
        mf.Finding("asset_doc", mf.UNBOUND),
    )
    assert_accounted(plan, job)
    plan = classify_packages(legacy(job))
    assert plan.primary.binding == mf.BINDING_SOLE_PACKAGE
    assert plan.primary.resources == ("asset_bin", "asset_tex", "asset_other")
    assert plan.findings == (mf.Finding("asset_doc", mf.UNBOUND),)
    assert_accounted(plan, job)


def test_gltf_resources_exclude_maps_bound_to_an_obj():
    job = legacy(derived_obj_package_job()) + [
        member("asset_gltf", "model/gltf+json"),
        member("asset_bin", "application/octet-stream"),
    ]
    assert classify_packages(job).unit("asset_gltf").resources == ("asset_bin",)


def placements(plan):
    """Every asset ID a plan places: unit files, candidate glTF resources, findings."""
    return (
        [asset_id for unit in plan.units for asset_id, _ in unit.files]
        + [asset_id for unit in plan.units for asset_id in unit.resources]
        + [finding.asset_id for finding in plan.findings]
    )


def assert_accounted(plan, members):
    """A job with a model file places each member exactly once; others place none."""
    if any(m.media_type.startswith("model/") or mf.model_format(m.media_type) for m in members):
        assert sorted(placements(plan)) == sorted(m.asset_id for m in members)
    else:
        assert placements(plan) == []


def test_maps_of_a_sole_oversized_obj_or_of_no_obj_are_reported_unbound():
    job = [
        member("asset_obj", "model/obj", size=300 * MiB),
        member("asset_mtl", "model/mtl"),
        member("asset_alb", "image/png", role="albedo"),
    ]
    plan = classify_packages(job)
    assert plan.units == ()
    assert plan.findings == (
        mf.Finding("asset_obj", mf.TOO_LARGE),
        mf.Finding("asset_mtl", mf.UNBOUND),
        mf.Finding("asset_alb", mf.UNBOUND),
    )
    for job in (
        [member("asset_glb", "model/glb"), member("asset_alb", "image/png", role="albedo")],
        [member("asset_mtl", "model/mtl"), member("asset_alb", "image/png", role="albedo")],
    ):
        plan = classify_packages(job)
        assert {f.asset_id: f.reason for f in plan.findings}["asset_alb"] == mf.UNBOUND
        assert_accounted(plan, job)


@pytest.mark.parametrize("role", ["smoothness", "height", "ao", "edge", "unknown"])
def test_stored_roles_without_a_material_slot_are_reported_unbound(role):
    job = [
        member("asset_obj", "model/obj"),
        member("asset_mtl", "model/mtl"),
        member("asset_alb", "image/png", role="albedo"),
        member("asset_map", "image/png", role=role),
    ]
    plan = classify_packages(job)
    assert plan.primary.textures == (("albedo", "asset_alb"),)
    assert plan.findings == (mf.Finding("asset_map", mf.UNBOUND),)
    assert_accounted(plan, job)


def test_lineage_reports_files_under_an_unsupported_model_as_unbound():
    job = [
        member("asset_glb", "model/glb", kind="img23d"),
        member("asset_stl", "model/stl", kind="3d23d", parent="asset_glb"),
        member("asset_alb", "image/png", role="albedo", kind="texture", parent="asset_stl"),
        member("asset_bin", "application/octet-stream", kind="texture", parent="asset_stl"),
    ]
    plan = classify_packages(job)
    assert [u.key for u in plan.units] == ["asset_glb"]
    assert plan.findings == (
        mf.Finding("asset_stl", mf.UNSUPPORTED_FORMAT),
        mf.Finding("asset_alb", mf.UNBOUND),
        mf.Finding("asset_bin", mf.UNBOUND),
    )
    assert_accounted(plan, job)


def test_a_reported_file_is_never_also_a_gltf_resource():
    job = [
        member("asset_obj", "model/obj"),
        member("asset_gltf", "model/gltf+json"),
        member("asset_alb", "image/png", role="albedo"),
        member("asset_bin", "application/octet-stream"),
    ]
    plan = classify_packages(job)
    assert plan.unit("asset_gltf").resources == ("asset_bin",)
    assert plan.findings == (mf.Finding("asset_alb", mf.NO_MATERIAL),)
    assert_accounted(plan, job)
    job = [
        member("asset_obj", "model/obj", size=250 * MiB),
        member("asset_mtl", "model/mtl"),
        member("asset_alb", "image/png", 250 * MiB, "albedo"),
        member("asset_nrm", "image/png", 100 * MiB, "normal"),
        member("asset_gltf", "model/gltf+json"),
    ]
    plan = classify_packages(job)
    assert [(u.key, u.resources) for u in plan.units] == [("asset_gltf", ())]
    assert {f.reason for f in plan.findings} == {mf.PACKAGE_TOO_LARGE}
    assert_accounted(plan, job)


def test_without_lineage_resources_beside_several_gltf_files_are_ambiguous():
    job = [
        member("asset_gltf_a", "model/gltf+json"),
        member("asset_gltf_b", "model/gltf+json"),
        member("asset_bin", "application/octet-stream"),
        member("asset_tex", "image/jpeg"),
        member("asset_doc", "text/plain"),
    ]
    plan = classify_packages(job)
    assert [(u.key, u.resources) for u in plan.units] == [
        ("asset_gltf_a", ()),
        ("asset_gltf_b", ()),
    ]
    assert {f.asset_id: f.reason for f in plan.findings} == {
        "asset_bin": mf.AMBIGUOUS_PACKAGE,
        "asset_tex": mf.AMBIGUOUS_PACKAGE,
        "asset_doc": mf.UNBOUND,
    }


_RANDOM_MEDIA = (
    "model/obj",
    "model/mtl",
    "model/gltf+json",
    "model/glb",
    "application/vnd.autodesk.fbx",
    "model/ply",
    "model/spz",
    "model/stl",
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/octet-stream",
    "text/plain",
    "video/mp4",
)
_RANDOM_ROLES = (None, "albedo", "base", "normal", "roughness", "metallic", "smoothness", "ao")
_RANDOM_SIZES = (None, 10, 1000, 5 * MiB, 9 * MiB, 200 * MiB, 300 * MiB)


@pytest.mark.parametrize("lineage", [False, True])
def test_every_saved_file_ends_in_exactly_one_unit_or_one_finding(lineage):
    rng = random.Random(366)
    for _ in range(1500):
        ids = [f"asset_{i}" for i in range(rng.randint(1, 12))]
        job = []
        for asset_id in ids:
            media = rng.choice(_RANDOM_MEDIA)
            role = rng.choice(_RANDOM_ROLES) if media.startswith("image/") else None
            kind = rng.choice(("txt23d", "img23d", "texture", "uploaded-3d")) if lineage else None
            parent = rng.choice([*ids, "asset_input", None]) if lineage else None
            job.append(
                PackageMember(asset_id, media, rng.choice(_RANDOM_SIZES), role, kind, parent)
            )
        plan = classify_packages(job)
        assert_accounted(plan, job)
        assert {f.reason for f in plan.findings} <= {
            mf.UNSUPPORTED_FORMAT,
            mf.TOO_LARGE,
            mf.PACKAGE_TOO_LARGE,
            mf.AMBIGUOUS_MATERIAL,
            mf.AMBIGUOUS_TEXTURE,
            mf.AMBIGUOUS_PACKAGE,
            mf.NO_MATERIAL,
            mf.UNBOUND,
        }


def test_stored_results_adapt_with_receipt_sizes_and_optional_lineage():
    digest = "a" * 64
    results = (
        StoredResult(
            ResultAsset("asset_obj", "000-obj.obj", "model/obj", None),
            DownloadedResult("000-obj.obj", 12, digest),
        ),
        StoredResult(ResultAsset("asset_alb", "001-alb.png", "image/png", 5, None, "albedo")),
    )
    assert members_from_results(results) == (
        PackageMember("asset_obj", "model/obj", 12),
        PackageMember("asset_alb", "image/png", 5, "albedo"),
    )
    lineage = {"asset_obj": ("txt23d", None), "asset_alb": ("3d-texture-albedo", "asset_obj")}
    adapted = members_from_results(results, lineage=lineage)
    assert adapted[1].parent_id == "asset_obj" and adapted[0].asset_type == "txt23d"
    assert classify_packages(adapted).lineage


@pytest.mark.parametrize(
    "fields",
    [
        ("../asset", "model/obj"),
        ("asset_a", ""),
        ("asset_a", "model/obj", -1),
        ("asset_a", "model/obj", True),
        ("asset_a", "model/obj", 1, 3),
        ("asset_a", "model/obj", 1, None, "Not A Type"),
        ("asset_a", "model/obj", 1, None, "txt23d", "https://x/y"),
    ],
)
def test_member_facts_are_validated(fields):
    with pytest.raises(ValueError):
        PackageMember(*fields)


def test_manifest_shape_is_bounded_and_unique():
    with pytest.raises(ValueError):
        classify_packages([member("asset_a", "model/obj")] * 2)
    with pytest.raises(ValueError):
        classify_packages([member(f"asset_{i}", "model/obj") for i in range(129)])
    with pytest.raises(ValueError):
        classify_packages(["asset_a"])


def test_classification_is_deterministic_for_the_same_manifest():
    job = derived_obj_package_job()
    assert classify_packages(job) == classify_packages(tuple(job))
    shuffled = job[:]
    random.Random(7).shuffle(shuffled)
    # Lineage binding does not depend on order; only ties use manifest order.
    assert classify_packages(shuffled).unit("asset_obj").files == (
        classify_packages(job).unit("asset_obj").files
    )


@pytest.mark.parametrize(
    ("fmt", "head"),
    [
        ("glb", struct.pack("<4sII", b"glTF", 2, 100)),
        ("gltf", b'\n  {"asset": {}}'),
        ("fbx", b"Kaydara FBX Binary\x20\x20\x00\x1a\x00\xe8\x1c\x00\x00"),
        ("obj", b"# comment\nv 0 0 0\n"),
        ("ply", b"ply\nformat ascii 1.0\n"),
        ("ply", b"ply\r\nformat ascii 1.0\r\n"),
        ("spz", b"\x1f\x8b\x08\x00"),
        ("spz", b"NGSP\x04\x00\x00\x00"),
        ("splat", b"\0" * 64),
    ],
)
def test_signatures_confirm_the_declared_format(fmt, head):
    check_signature(fmt, head, 64)


@pytest.mark.parametrize(
    ("fmt", "head", "size"),
    [
        ("glb", struct.pack("<4sII", b"glTF", 1, 100), 64),
        ("glb", b"glTF", 64),
        ("gltf", b"\xef\xbb\xbf{}", 64),
        ("fbx", b"; FBX 7.4.0 project file\n", 64),
        ("obj", b"v 0 0 0\0", 64),
        ("ply", b"PLY\n", 64),
        ("spz", b"PK\x03\x04", 64),
        ("splat", b"\0" * 64, 65),
        ("obj", b"v 0 0 0\n", 0),
        ("obj", b"v 0 0 0\n", MAX_MEMBER_BYTES + 1),
    ],
)
def test_signature_mismatches_fail_closed(fmt, head, size):
    with pytest.raises(ModelPackageError):
        check_signature(fmt, head, size)


SPLAT_PROPERTIES = (
    "x y z nx ny nz f_dc_0 f_dc_1 f_dc_2 opacity scale_0 scale_1 scale_2 rot_0 rot_1 rot_2 rot_3"
).split()


def ply(encoding="binary_little_endian", vertices=3, properties=None, extra="", newline="\n"):
    lines = ["ply", f"format {encoding} 1.0", "comment end_header is only a word here"]
    lines.append(f"element vertex {vertices}")
    lines += [f"property float {name}" for name in properties or SPLAT_PROPERTIES]
    lines += [line for line in extra.split("|") if line]
    lines.append("end_header")
    return (newline.join(lines) + newline).encode("ascii")


def test_gaussian_splat_ply_is_classified_from_its_header():
    header = ply()
    result = inspect_ply_header(header + b"\0" * 64, size=len(header) + 3 * 17 * 4)
    assert result.kind is UnitKind.SPLAT and result.vertices == 3 and result.faces == 0
    assert result.header_bytes == len(header) and result.encoding == "binary_little_endian"
    assert result.vertex_properties == tuple(SPLAT_PROPERTIES)
    assert inspect_ply_header(ply(newline="\r\n")).kind is UnitKind.SPLAT
    with pytest.raises(ModelPackageError, match="does not match"):
        inspect_ply_header(header, size=len(header) + 3 * 17 * 4 - 1)
    with pytest.raises(ModelPackageError, match="does not match"):
        inspect_ply_header(header, size=len(header) + 3 * 17 * 4 + 4)


@pytest.mark.parametrize(
    "header",
    [
        ply(extra="element face 1|property list uchar int vertex_indices"),
        ply(encoding="ascii"),
        ply(encoding="binary_big_endian"),
        ply(properties=[p for p in SPLAT_PROPERTIES if p != "opacity"]),
        ply(properties=["x", "y", "z"]),
        ply(extra="property list uchar float extra"),
        ply().replace(b"property float x\n", b"property double x\n"),
    ],
)
def test_other_well_formed_ply_headers_import_as_meshes(header):
    assert inspect_ply_header(header, size=1).kind is UnitKind.MESH


def test_an_empty_face_element_and_any_comment_encoding_keep_the_splat_route():
    header = ply(extra="element face 0|property list uchar int vertex_indices")
    assert inspect_ply_header(header).kind is UnitKind.SPLAT
    header = ply().replace(b"is only a word here", "cr\xe9\xe9".encode("latin-1"))
    assert inspect_ply_header(header).kind is UnitKind.SPLAT


@pytest.mark.parametrize("separator", ["\x85", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\r"])
def test_ply_header_lines_split_only_at_line_feeds(separator):
    comment = f"a{separator}element face 3{separator}property list uchar int vertex_indices"
    header = ply().replace(b"is only a word here", comment.encode("latin-1"))
    result = inspect_ply_header(header)
    assert (result.kind, result.faces) == (UnitKind.SPLAT, 0)


@pytest.mark.parametrize(
    "data",
    [
        b"obj\n",
        ply(extra="element vertex 2|property float x"),
        ply(extra="element face 0|element face 1"),
        ply(properties=[*SPLAT_PROPERTIES, "x"]),
        ply(extra="element face 0|property list uchar int i|property list uchar int i"),
        ply().replace(b"element vertex 3", b"element vertex 3\x0c"),
        ply().replace(b"element vertex 3", b"element\x1cvertex 3"),
        ply().replace(b"end_header", b"end_head"),
        ply().replace(b"format binary_little_endian 1.0", b"format binary_little_endian 2.0"),
        ply().replace(b"element vertex 3", b"element vertex -3"),
        ply().replace(b"element vertex 3", b"element vertex 99999999999"),
        ply().replace(b"property float x", b"property quad x"),
        ply().replace(b"property float x", b"propertyfloat x"),
        ply().replace(b"property float x", "property float \xe9".encode("latin-1")),
        ply(extra="|".join(f"element extra{i} 0" for i in range(16))),
        b"ply\nformat ascii 1.0\n" + b"comment x\n" * 7000 + b"end_header\n",
        ply().replace(b"format binary_little_endian 1.0\n", b""),
    ],
)
def test_malformed_ply_headers_fail_closed(data):
    with pytest.raises(ModelPackageError):
        inspect_ply_header(data)
