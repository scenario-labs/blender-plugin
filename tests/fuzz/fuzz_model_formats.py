# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fuzz the classification of saved 3D results in ``core.scene.model_formats``.

``inspect_ply_header`` and ``check_signature`` raise only ModelPackageError on any
bytes, and an accepted PLY header lies within its bounded prefix; a splat header is
binary little-endian with vertices, no faces and a body that fits a known size.
``classify_packages`` follows its documented plan: once a job holds a model file,
every member is in exactly one unit's files, one glTF unit's resources or one
finding; companions bind through ``parent_id`` with lineage and to the job's only
file of that format without it; main units sort first and the first is primary.
"""

import sys
from collections import Counter

from samples import MESH_PLY, SPLAT_PROPERTIES, splat_ply
from support import DataProvider, mostly, split

from scenario.core.scene import model_formats as formats
from scenario.core.scene.model_formats import ModelFormat, ModelPackageError, UnitKind

PROVIDER = DataProvider
MIB = 1024 * 1024
IDS = ["a", "b", "c", "d", "e", "f", "g", "h"]
# (media type, texture role, parent index, SDK asset type) of a job with two packages.
TEMPLATE = [
    ("model/obj", None, None, "img23d"),
    ("model/mtl", None, 0, "convert"),
    ("image/png", "albedo", 1, "texture"),
    ("model/gltf+json", None, None, "txt23d"),
    ("application/octet-stream", None, 3, "convert"),
    ("image/jpeg", "normal", 0, "texture"),
    ("model/gltf-binary", None, None, "3d23d"),
    ("model/ply", None, None, "img2splat"),
]
MEDIA = sorted({media for types in formats.FORMAT_MEDIA_TYPES.values() for media in types})
MEDIA += ["model/mtl", "model/stl", "model/vnd.usdz+zip", "model/", "image/png", "image/jpeg"]
MEDIA += ["image/jpg", "image/webp", "image/gif", "application/octet-stream", "video/mp4"]
MEDIA += ["application/gltf-buffer", "text/plain"]
ROLES = [None, "albedo", "base", "normal", "roughness", "metallic", "height", "ao", "x"]
TYPES = ["img23d", "txt23d", "3d23d", "video23d", "img2splat", "convert", "texture"]
SIZES = [None, 0, 1, 4 * MIB, 4 * MIB + 1, 8 * MIB, 8 * MIB + 1, 256 * MIB, 256 * MIB + 1]
SIZES += [300 * MIB, 600 * MIB]
REASONS = {
    formats.UNSUPPORTED_FORMAT,
    formats.TOO_LARGE,
    formats.PACKAGE_TOO_LARGE,
    formats.AMBIGUOUS_MATERIAL,
    formats.AMBIGUOUS_TEXTURE,
    formats.AMBIGUOUS_PACKAGE,
    formats.NO_MATERIAL,
    formats.UNBOUND,
}
TYPES_PLY = ["char", "uchar", "int8", "short", "int", "uint32", "float", "float32", "double"]
TYPES_PLY += ["float64", "list", "float128", ""]
COUNTS = ["0", "1", "3", "2147483647", "2147483648", "99999999999", "-1", "+3", "٣", "x"]
NAMES = [*SPLAT_PROPERTIES, "vertex", "face", "nx", "x"]
LINES = ["format binary_big_endian 1.0", "format ascii 2.0", "element face 1", "element vertex 3"]
LINES += ["element vertex 2147483648", "property float x", "property float y"]
LINES += ["property list uchar int vertex_indices", "comment \xff\xfe", "obj_info x", "", "\t"]
LINES += ["element", "property", "end_header", "ply", "property uchar"]


def ply(fdp):
    """A valid mesh or splat PLY whose header has one to three hostile edits."""
    template = MESH_PLY if fdp.ConsumeBool() else splat_ply()
    header, body = template.split(b"end_header\n")
    lines = header.decode("ascii").split("\n")[:-1]
    for _ in range(fdp.ConsumeIntInRange(1, 3)):
        index = fdp.ConsumeIntInRange(1, len(lines))
        edit = fdp.ConsumeIntInRange(0, 5)
        if edit == 0:
            elements = [i for i, line in enumerate(lines) if line.startswith("element ")]
            if elements:
                chosen = fdp.PickValueInList(elements)
                name = lines[chosen].split()[1]
                lines[chosen] = f"element {name} {fdp.PickValueInList(COUNTS)}"
        elif edit == 1:
            lines.insert(index, fdp.PickValueInList(LINES))
        elif edit == 2 and index < len(lines):
            lines[index] = lines[index].replace(
                " ", fdp.PickValueInList(["\t", "  ", " \t", "\x0b"])
            )
        elif edit == 3:
            lines.insert(index, lines[index - 1])
        elif edit == 4 and index < len(lines):
            del lines[index]
        elif edit == 5 and index < len(lines):
            kind = fdp.PickValueInList(TYPES_PLY)
            lines[index] = f"property {kind} {fdp.PickValueInList(NAMES)}"
    ending = fdp.PickValueInList(["\n", "\n", "\r\n"])
    terminator = fdp.PickValueInList(["end_header", "end_header", "end_header \r", "end_headers"])
    text = ending.join([*lines, terminator]) + ending
    if fdp.ConsumeBool():
        body = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 96))
    return text.encode("utf-8") + body


def check_ply(data, size):
    try:
        header = formats.inspect_ply_header(data, size=size)
    except ModelPackageError:
        return
    prefix = data[: header.header_bytes]
    assert header.header_bytes <= formats.MAX_PLY_HEADER_BYTES and prefix.endswith(b"\n")
    assert b"\nend_header" in prefix
    assert header.encoding in {"ascii", "binary_little_endian", "binary_big_endian"}
    assert 0 <= header.vertices <= 2**31 - 1 and 0 <= header.faces <= 2**31 - 1
    if header.kind is UnitKind.SPLAT:
        assert header.encoding == "binary_little_endian" and header.vertices > 0
        assert header.faces == 0 and set(SPLAT_PROPERTIES) <= set(header.vertex_properties)
        properties = len(header.vertex_properties)
        assert size is None or size >= header.header_bytes + header.vertices * (properties + 30)
    else:
        assert header.kind is UnitKind.MESH


def check_signature(fdp):
    fmt = fdp.PickValueInList(list(ModelFormat))
    size = fdp.PickValueInList([0, 1, 31, 32, 64, 256 * MIB, 256 * MIB + 1, -1, True, 2.0])
    head = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 80))
    try:
        formats.check_signature(fmt, head, size)
    except ModelPackageError:
        return
    assert type(size) is int and 0 < size <= formats.MAX_MEMBER_BYTES
    head = head[:64]
    expected = {
        ModelFormat.GLB: head[:4] == b"glTF" and head[4:8] == b"\2\0\0\0",
        ModelFormat.GLTF: head.lstrip(b" \t\r\n")[:1] == b"{",
        ModelFormat.FBX: head.startswith(b"Kaydara FBX Binary  \0"),
        ModelFormat.OBJ: b"\0" not in head,
        ModelFormat.PLY: head.startswith((b"ply\n", b"ply\r\n")),
        ModelFormat.SPZ: head.startswith((b"\x1f\x8b", b"NGSP")),
        ModelFormat.SPLAT: size % 32 == 0,
    }
    assert expected[fmt], f"{fmt} accepted {head!r}"


def members(fdp):
    """An OBJ, a glTF and their companions, then a GLB and a PLY, each part mostly kept."""
    lineage = fdp.ConsumeBool()
    found = []
    for index in range(fdp.ConsumeIntInRange(0, len(TEMPLATE))):
        media, role, parent, asset_type = TEMPLATE[index]
        # Unique IDs, except for an occasional duplicate the classifier must refuse.
        asset_id = mostly(fdp, [IDS[index]], IDS)
        typed = lineage or not fdp.ConsumeIntInRange(0, 3)
        asset_type = mostly(fdp, [asset_type], TYPES) if typed else None
        parent = mostly(fdp, [None if parent is None else IDS[parent]], [None, *IDS])
        try:
            member = formats.PackageMember(
                asset_id,
                mostly(fdp, [media], MEDIA),
                mostly(fdp, [None, 1, MIB], SIZES),
                mostly(fdp, [role], ROLES),
                asset_type,
                parent if asset_type is not None else None,
            )
        except ValueError:
            continue  # A member refuses fields that are not manifest facts.
        found.append(member)
    return found


def check_classification(fdp):
    found = members(fdp)
    ply_kinds = {
        fdp.PickValueInList(IDS): fdp.PickValueInList(["mesh", "splat", "other"])
        for _ in range(fdp.ConsumeIntInRange(0, 2))
    }
    by_id = {member.asset_id: member for member in found}
    invalid = len(by_id) != len(found) or any(
        key not in by_id
        or formats.model_format(by_id[key].media_type) is not ModelFormat.PLY
        or value not in {"mesh", "splat"}
        for key, value in ply_kinds.items()
    )
    try:
        plan = formats.classify_packages(found, ply_kinds=ply_kinds)
    except ValueError:
        assert invalid, "a valid manifest was refused"
        return
    assert not invalid, "an invalid manifest was classified"
    check_plan(plan, found, by_id, ply_kinds)


def check_plan(plan, found, by_id, ply_kinds):
    order = [member.asset_id for member in found]
    lineage = bool(found) and all(member.asset_type is not None for member in found)
    assert plan.lineage == lineage
    if not any(
        formats.model_format(m.media_type) or m.media_type.startswith("model/") for m in found
    ):
        assert plan.units == () and plan.findings == (), "a job without models has no plan"
        return
    places = Counter(finding.asset_id for finding in plan.findings)
    for unit in plan.units:
        places.update(asset_id for asset_id, _ in unit.files)
        places.update(unit.resources)
    assert set(places) == set(order), "every member has a place"
    assert all(count == 1 for count in places.values()), f"a member has two places: {places}"
    assert all(finding.reason in REASONS for finding in plan.findings)
    findings = [order.index(finding.asset_id) for finding in plan.findings]
    assert findings == sorted(findings), "findings follow the manifest"
    assert [unit.primary for unit in plan.units] == [i == 0 for i in range(len(plan.units))]
    mains = [unit.main for unit in plan.units]
    assert mains == sorted(mains, reverse=True), "main units sort first"
    for unit in plan.units:
        check_unit(unit, by_id, lineage, ply_kinds)


def check_unit(unit, by_id, lineage, ply_kinds):
    member = by_id[unit.key]
    assert unit.format == formats.model_format(member.media_type)
    assert unit.files[0] == (unit.key, f"model.{unit.format.value}")
    assert len({name for _, name in unit.files}) == len(unit.files)
    assert unit.main == (
        lineage and member.asset_type in formats.MAIN_ASSET_TYPES and member.parent_id not in by_id
    )
    if unit.format is ModelFormat.PLY:
        assert unit.kind == UnitKind(ply_kinds.get(unit.key, "ply"))
    companions = [by_id[asset_id] for asset_id, _ in unit.files[1:]] + [
        by_id[asset_id] for asset_id in unit.resources
    ]
    gltf = unit.format is ModelFormat.GLTF
    assert (member.size or 0) <= (formats.MAX_GLTF_JSON_BYTES if gltf else formats.MAX_MEMBER_BYTES)
    bound = [member] + [by_id[asset_id] for asset_id, _ in unit.files[1:]]
    assert sum(item.size or 0 for item in bound) <= formats.MAX_PACKAGE_BYTES
    if unit.material is not None:
        assert unit.format is ModelFormat.OBJ
        assert (unit.material, "material.mtl") in unit.files
        assert by_id[unit.material].media_type in formats.MATERIAL_MEDIA_TYPES
    slots = [slot for slot, _ in unit.textures]
    assert len(set(slots)) == len(slots) and set(slots) <= set(formats.TEXTURE_SLOTS)
    assert not unit.textures or unit.material is not None, "maps bind only with a material"
    assert len(unit.texture_files) == len(unit.textures)
    assert not unit.resources or unit.format is ModelFormat.GLTF
    if unit.binding == formats.BINDING_SINGLE:
        assert not companions
    elif unit.binding == formats.BINDING_SOLE_PACKAGE:
        assert not lineage
        peers = [m for m in by_id.values() if formats.model_format(m.media_type) is unit.format]
        assert len(peers) == 1, "a package binds only beside no other file of its format"
    else:
        assert unit.binding == formats.BINDING_PARENT and lineage
        for companion in companions:
            parents = {unit.key, unit.material}
            assert companion.parent_id in parents, "companions bind through parent_id"


def TestOneInput(data):
    mode, rest = split(data)
    mode %= 5
    if mode < 2:
        check_ply(rest, len(rest) if mode == 1 else None)
        return
    fdp = PROVIDER(rest)
    if mode == 2:
        check_signature(fdp)
    elif mode == 3:
        check_classification(fdp)
    else:
        body = ply(fdp)
        check_ply(body, len(body) if fdp.ConsumeBool() else None)


if __name__ == "__main__":
    import atheris

    PROVIDER = atheris.FuzzedDataProvider
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
