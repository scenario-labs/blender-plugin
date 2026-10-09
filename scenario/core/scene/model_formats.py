# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Classify a saved job's 3D result files into explicit import units. No bpy.

Inputs are URL-free manifest facts typed by the pinned SDK 2.2.0
(``scenario_sdk/types/asset_retrieve_response.py``): ``Asset.mime_type``,
``AssetProperties.size``, ``AssetMetadata.type`` and ``AssetMetadata.parent_id``.
Undocumented provider filenames are never used. The MIME type selects handling;
file bytes are only checked against the declared format, never sniffed to choose one.
Classification orders units for display and imports nothing.
"""

import re
import struct
from dataclasses import dataclass
from enum import StrEnum

from ..jobs.store import _identity
from .glb import MAX_JSON_BYTES

# Equal to the signed-storage per-file default and the GLB preflight limit.
MAX_MEMBER_BYTES = 256 * 1024 * 1024
MAX_PACKAGE_BYTES = 512 * 1024 * 1024
MAX_MTL_BYTES = 4 * 1024 * 1024
MAX_GLTF_JSON_BYTES = MAX_JSON_BYTES
MAX_PLY_HEADER_BYTES = 64 * 1024
MAX_MANIFEST_MEMBERS = 128


class ModelPackageError(ValueError):
    """Keep the saved files for another explicit import policy."""


class ModelFormat(StrEnum):
    GLB = "glb"
    GLTF = "gltf"
    FBX = "fbx"
    OBJ = "obj"
    PLY = "ply"
    SPZ = "spz"
    SPLAT = "splat"


class UnitKind(StrEnum):
    MESH = "mesh"
    SPLAT = "splat"
    # Mesh or Gaussian splat, decided by inspect_ply_header on verified bytes.
    PLY = "ply"


# MIME aliases. SDK 2.2.0 Asset.original_mime_type lists this model family.
FORMAT_MEDIA_TYPES = {
    ModelFormat.GLB: frozenset({"model/gltf-binary", "model/glb"}),
    ModelFormat.GLTF: frozenset({"model/gltf+json"}),
    ModelFormat.FBX: frozenset(
        {"model/x-fbx", "application/vnd.autodesk.fbx", "application/x.autodesk.fbx"}
    ),
    ModelFormat.OBJ: frozenset({"model/obj"}),
    ModelFormat.PLY: frozenset({"model/ply", "application/x-ply"}),
    ModelFormat.SPZ: frozenset({"model/spz"}),
    ModelFormat.SPLAT: frozenset({"model/splat"}),
}
_FORMAT_BY_MEDIA = {media: fmt for fmt, types in FORMAT_MEDIA_TYPES.items() for media in types}
MATERIAL_MEDIA_TYPES = frozenset({"model/mtl"})
BUFFER_MEDIA_TYPES = frozenset({"application/octet-stream", "application/gltf-buffer"})
TEXTURE_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
}

# Generated root outputs (AssetMetadata.type); derived conversions name a parent.
MAIN_ASSET_TYPES = frozenset({"img23d", "txt23d", "3d23d", "video23d", "img2splat"})

# Material slots referenced by MTL map statements, keyed by stored texture role.
TEXTURE_SLOTS = ("albedo", "normal", "roughness", "metallic")
_SLOT_BY_ROLE = {
    "albedo": "albedo",
    "base": "albedo",
    "normal": "normal",
    "roughness": "roughness",
    "metallic": "metallic",
}

_MESH_FORMATS = frozenset({ModelFormat.GLB, ModelFormat.GLTF, ModelFormat.FBX, ModelFormat.OBJ})
_RANK = {
    ModelFormat.GLB: 0,
    ModelFormat.GLTF: 1,
    ModelFormat.FBX: 2,
    ModelFormat.OBJ: 3,
    ModelFormat.SPZ: 5,
    ModelFormat.SPLAT: 7,
}

# Finding reasons are stable codes for later status surfaces.
UNSUPPORTED_FORMAT = "unsupported-format"
TOO_LARGE = "too-large"
PACKAGE_TOO_LARGE = "package-too-large"
AMBIGUOUS_MATERIAL = "ambiguous-material"
AMBIGUOUS_TEXTURE = "ambiguous-texture"
AMBIGUOUS_PACKAGE = "ambiguous-package"
NO_MATERIAL = "no-material"
UNBOUND = "unbound"

BINDING_SINGLE = "single"
BINDING_PARENT = "parent"
BINDING_SOLE_PACKAGE = "sole-package"


def model_format(media_type):
    """Return the import format for a normalized MIME type, or None."""
    return _FORMAT_BY_MEDIA.get(media_type) if isinstance(media_type, str) else None


def unsupported_model(media_type):
    """A model/* result with no import policy, such as ksplat, sog, STL or USD."""
    return (
        isinstance(media_type, str)
        and media_type.startswith("model/")
        and media_type not in _FORMAT_BY_MEDIA
        and media_type not in MATERIAL_MEDIA_TYPES
    )


@dataclass(frozen=True)
class PackageMember:
    """One saved job result, in job manifest order.

    ``size`` is the verified receipt size when available. ``asset_type`` and
    ``parent_id`` are SDK ``AssetMetadata.type`` and ``AssetMetadata.parent_id``;
    the store does not persist them, so they are None unless a caller supplies them.
    """

    asset_id: str
    media_type: str
    size: int | None = None
    texture_role: str | None = None
    asset_type: str | None = None
    parent_id: str | None = None

    def __post_init__(self):
        _identity(self.asset_id)
        if not isinstance(self.media_type, str) or not self.media_type:
            raise ValueError("Use a normalized media type")
        if self.size is not None and (type(self.size) is not int or self.size < 0):
            raise ValueError("Use a nonnegative integer size")
        if self.texture_role is not None and not isinstance(self.texture_role, str):
            raise ValueError("Use a stored texture role")
        if self.asset_type is not None and (
            not isinstance(self.asset_type, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9:-]{0,63}", self.asset_type)
        ):
            raise ValueError("Use an SDK asset metadata type")
        if self.parent_id is not None:
            _identity(self.parent_id)


def members_from_results(results, *, lineage=None):
    """Adapt saved results; ``lineage`` maps asset IDs to (type, parent_id) facts."""
    members = []
    for item in results:
        asset = item.asset
        receipt = item.receipt
        facts = (lineage or {}).get(asset.asset_id) or (None, None)
        members.append(
            PackageMember(
                asset.asset_id,
                asset.media_type,
                receipt.size if receipt is not None else asset.expected_size,
                asset.texture_role,
                *facts,
            )
        )
    return tuple(members)


@dataclass(frozen=True)
class Finding:
    """A saved file that is not imported, with a stable reason code."""

    asset_id: str
    reason: str


@dataclass(frozen=True)
class ImportUnit:
    """One explicit import choice; only ``files`` may appear in its private snapshot."""

    key: str
    format: ModelFormat
    kind: UnitKind
    primary: bool
    main: bool
    binding: str
    material: str | None = None
    textures: tuple[tuple[str, str], ...] = ()
    resources: tuple[str, ...] = ()
    files: tuple[tuple[str, str], ...] = ()

    @property
    def members(self):
        """Asset IDs a durable application claim must cover, before glTF resources."""
        return tuple(asset_id for asset_id, _ in self.files)


@dataclass(frozen=True)
class PackagePlan:
    units: tuple[ImportUnit, ...]
    findings: tuple[Finding, ...]
    lineage: bool

    @property
    def primary(self):
        return self.units[0] if self.units else None

    def unit(self, key):
        matches = [unit for unit in self.units if unit.key == key]
        return matches[0] if matches else None


def _texture_slot(member):
    if member.media_type not in TEXTURE_EXTENSIONS or member.texture_role is None:
        return None
    return _SLOT_BY_ROLE.get(member.texture_role)


def _kind(fmt, asset_id, ply_kinds):
    if fmt in _MESH_FORMATS:
        return UnitKind.MESH
    if fmt is ModelFormat.PLY:
        return UnitKind(ply_kinds[asset_id]) if asset_id in ply_kinds else UnitKind.PLY
    return UnitKind.SPLAT


def _rank(fmt, kind):
    if fmt is ModelFormat.PLY:
        return 4 if kind is UnitKind.MESH else 6
    return _RANK[fmt]


def _too_large(member, limit):
    return member.size is not None and member.size > limit


class _Classifier:
    def __init__(self, members, ply_kinds):
        self.members = members
        self.index = {member.asset_id: i for i, member in enumerate(members)}
        self.lineage = bool(members) and all(m.asset_type is not None for m in members)
        self.ply_kinds = ply_kinds
        self.findings = {}

    def report(self, member, reason):
        self.findings.setdefault(member.asset_id, reason)

    def children(self, parent):
        return [m for m in self.members if self.lineage and m.parent_id == parent.asset_id]

    def pool(self, primary, peers):
        """Companion candidates: children with lineage, else a job with one such unit."""
        if self.lineage:
            pool, binding = self.children(primary), BINDING_PARENT
        elif len(peers) == 1:
            pool, binding = self.members, BINDING_SOLE_PACKAGE
        else:
            return [], BINDING_SINGLE
        # Other model files are separate units, never companions.
        return [m for m in pool if model_format(m.media_type) is None], binding

    def obj_companions(self, obj, peers, claimed):
        pool, binding = self.pool(obj, peers)
        pool = [m for m in pool if m.asset_id not in claimed]
        materials = [m for m in pool if m.media_type in MATERIAL_MEDIA_TYPES]
        material = None
        if len(materials) == 1 and not _too_large(materials[0], MAX_MTL_BYTES):
            material = materials[0]
        for candidate in materials:
            if candidate is not material:
                self.report(candidate, AMBIGUOUS_MATERIAL if len(materials) > 1 else TOO_LARGE)
        if material is not None and self.lineage:
            pool += [
                m
                for m in self.children(material)
                if m.asset_id not in claimed and model_format(m.media_type) is None
            ]
        slots = {}
        for member in pool:
            slot = _texture_slot(member)
            if slot is not None:
                slots.setdefault(slot, []).append(member)
            elif self.lineage and member.media_type not in MATERIAL_MEDIA_TYPES:
                self.report(member, UNBOUND)
        textures = []
        for slot in TEXTURE_SLOTS:
            candidates = slots.get(slot, [])
            for member in candidates:
                if len(candidates) > 1:
                    self.report(member, AMBIGUOUS_TEXTURE)
                elif material is None:
                    self.report(member, NO_MATERIAL)
                elif _too_large(member, MAX_MEMBER_BYTES):
                    self.report(member, TOO_LARGE)
                else:
                    textures.append((slot, member))
        return binding, material, textures

    def gltf_resources(self, gltf, peers, claimed):
        pool, binding = self.pool(gltf, peers)
        resources = [
            m.asset_id
            for m in pool
            if m.asset_id not in claimed
            and (m.media_type in BUFFER_MEDIA_TYPES or m.media_type in TEXTURE_EXTENSIONS)
        ]
        return binding, tuple(resources)

    def classify(self):
        candidates, peers = [], {}
        for member in self.members:
            fmt = model_format(member.media_type)
            if fmt is None:
                if unsupported_model(member.media_type):
                    self.report(member, UNSUPPORTED_FORMAT)
                continue
            # Oversized files still count, so companions never bind to the other one.
            peers.setdefault(fmt, []).append(member)
            limit = MAX_GLTF_JSON_BYTES if fmt is ModelFormat.GLTF else MAX_MEMBER_BYTES
            if _too_large(member, limit):
                self.report(member, TOO_LARGE)
                continue
            candidates.append((member, fmt))
        objs = peers.get(ModelFormat.OBJ, [])
        gltfs = peers.get(ModelFormat.GLTF, [])
        claimed, units = set(), []
        # OBJ packages bind first; glTF candidates exclude their companions.
        ordered = sorted(candidates, key=lambda entry: entry[1] is not ModelFormat.OBJ)
        for member, fmt in ordered:
            binding, material, textures, resources = BINDING_SINGLE, None, [], ()
            if fmt is ModelFormat.OBJ:
                binding, material, textures = self.obj_companions(member, objs, claimed)
            elif fmt is ModelFormat.GLTF:
                binding, resources = self.gltf_resources(member, gltfs, claimed)
            bound = [member] + ([material] if material else []) + [m for _, m in textures]
            if sum(m.size or 0 for m in bound) > MAX_PACKAGE_BYTES:
                for item in bound:
                    self.report(item, PACKAGE_TOO_LARGE)
                continue
            claimed.update(m.asset_id for m in bound[1:])
            files = [(member.asset_id, f"model.{fmt.value}")]
            if material is not None:
                files.append((material.asset_id, "material.mtl"))
            files += [
                (m.asset_id, f"texture-{slot}.{TEXTURE_EXTENSIONS[m.media_type]}")
                for slot, m in textures
            ]
            kind = _kind(fmt, member.asset_id, self.ply_kinds)
            main = (
                self.lineage
                and member.asset_type in MAIN_ASSET_TYPES
                and member.parent_id not in self.index
            )
            order = (
                not main,
                _rank(fmt, kind),
                -(len(bound) - 1),
                -(member.size or 0),
                self.index[member.asset_id],
            )
            units.append(
                (
                    order,
                    dict(
                        key=member.asset_id,
                        format=fmt,
                        kind=kind,
                        main=main,
                        binding=binding,
                        material=material.asset_id if material else None,
                        textures=tuple((slot, m.asset_id) for slot, m in textures),
                        resources=resources,
                        files=tuple(files),
                    ),
                )
            )
        self.report_leftovers(objs, claimed)
        units.sort(key=lambda entry: entry[0])
        return PackagePlan(
            tuple(
                ImportUnit(primary=position == 0, **fields)
                for position, (_, fields) in enumerate(units)
            ),
            tuple(
                Finding(asset_id, reason)
                for asset_id, reason in sorted(
                    self.findings.items(), key=lambda entry: self.index[entry[0]]
                )
            ),
            self.lineage,
        )

    def report_leftovers(self, objs, claimed):
        for member in self.members:
            if member.asset_id in claimed or member.asset_id in self.findings:
                continue
            if member.media_type in MATERIAL_MEDIA_TYPES:
                self.report(member, AMBIGUOUS_PACKAGE if len(objs) > 1 else UNBOUND)
            elif not self.lineage and len(objs) > 1 and _texture_slot(member) is not None:
                self.report(member, AMBIGUOUS_PACKAGE)


def classify_packages(members, *, ply_kinds=None):
    """Group saved results into ordered import units; the first unit is primary.

    With SDK lineage (every member has ``asset_type``), companions bind only through
    ``parent_id`` and generated root outputs of a main 3D type sort first. Without
    it, an OBJ or glTF binds companions only when it is the job's only file of that
    format, oversized ones included. Within each group units sort by format, then
    more bound companions, larger size and manifest order. Ambiguous, unsupported
    and oversized files stay saved and are reported, never guessed.
    ``ply_kinds`` optionally maps PLY asset IDs to "mesh" or "splat" from
    :func:`inspect_ply_header` on verified bytes.
    """
    members = tuple(members)
    if len(members) > MAX_MANIFEST_MEMBERS or not all(
        isinstance(member, PackageMember) for member in members
    ):
        raise ValueError("Use a bounded manifest of package members")
    if len({member.asset_id for member in members}) != len(members):
        raise ValueError("Package members must be unique")
    ply_kinds = dict(ply_kinds or {})
    formats = {member.asset_id: model_format(member.media_type) for member in members}
    if any(
        formats.get(key) is not ModelFormat.PLY or value not in {"mesh", "splat"}
        for key, value in ply_kinds.items()
    ):
        raise ValueError("Classify only saved PLY members as mesh or splat")
    return _Classifier(members, ply_kinds).classify()


_FBX_MAGIC = b"Kaydara FBX Binary\x20\x20\x00\x1a\x00"


def check_signature(fmt, head, size):
    """Confirm the leading bytes match the declared format; never choose a format.

    ``head`` holds at least the first 64 bytes when the file is that large.
    """
    fmt = ModelFormat(fmt)
    if type(size) is not int or not 0 < size <= MAX_MEMBER_BYTES:
        raise ModelPackageError("Saved model size is outside the supported import limit")
    head = bytes(head[:64])
    if fmt is ModelFormat.GLB:
        valid = len(head) >= 12 and struct.unpack_from("<4sI", head) == (b"glTF", 2)
    elif fmt is ModelFormat.GLTF:
        valid = head.lstrip(b" \t\r\n")[:1] == b"{"
    elif fmt is ModelFormat.FBX:
        # Blender's bundled FBX add-on reads the binary encoding only.
        valid = head.startswith(_FBX_MAGIC)
    elif fmt is ModelFormat.OBJ:
        valid = b"\0" not in head
    elif fmt is ModelFormat.PLY:
        valid = head.startswith((b"ply\n", b"ply\r\n"))
    elif fmt is ModelFormat.SPZ:
        # Gzip-wrapped SPZ, or a raw NGSP header; decoding checks the version.
        valid = head.startswith((b"\x1f\x8b", b"NGSP"))
    else:
        valid = size % 32 == 0
    if not valid:
        raise ModelPackageError(f"The saved file is not a supported {fmt.value.upper()} file")


_PLY_TYPES = {
    "char": 1,
    "int8": 1,
    "uchar": 1,
    "uint8": 1,
    "short": 2,
    "int16": 2,
    "ushort": 2,
    "uint16": 2,
    "int": 4,
    "int32": 4,
    "uint": 4,
    "uint32": 4,
    "float": 4,
    "float32": 4,
    "double": 8,
    "float64": 8,
}
_PLY_ENCODINGS = ("ascii", "binary_little_endian", "binary_big_endian")
_SPLAT_PROPERTIES = (
    "x",
    "y",
    "z",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
)


@dataclass(frozen=True)
class PlyHeader:
    kind: UnitKind
    encoding: str
    vertices: int
    faces: int
    header_bytes: int
    vertex_properties: tuple[str, ...]


def inspect_ply_header(data, *, size=None):
    """Classify a PLY as a Gaussian splat or a mesh from its bounded header.

    The splat route needs binary little-endian float32 x, y, z, f_dc_0..2, opacity
    and scale_0..2 scalar vertex properties, no face data and, when ``size`` is
    known, an exact body length. Any other well-formed header is a mesh PLY. Lines
    end at LF only and element names must be unique.
    """
    data = bytes(data[:MAX_PLY_HEADER_BYTES])
    if not data.startswith((b"ply\n", b"ply\r\n")):
        raise ModelPackageError("The saved file is not a PLY file")
    terminator = re.search(rb"\nend_header[ \t\r]*\n", data)
    if terminator is None:
        raise ModelPackageError("PLY header is incomplete or exceeds the supported import limit")
    header_bytes = terminator.end()
    encoding, elements = None, []
    try:
        # PLY readers split header lines at LF only. Comments may use any
        # encoding; structural lines are printable ASCII separated by spaces or tabs.
        for raw in data[: terminator.start()].split(b"\n")[1:]:
            line = raw[:-1] if raw.endswith(b"\r") else raw
            if line.split()[:1] in ([b"comment"], [b"obj_info"], []):
                continue
            if re.search(rb"[^\t\x20-\x7e]", line):
                raise ValueError
            words = line.decode("ascii").split()
            if words[0] == "format" and encoding is None and not elements:
                if words[1:] not in ([name, "1.0"] for name in _PLY_ENCODINGS):
                    raise ValueError
                encoding = words[1]
            elif words[0] == "element" and len(words) == 3 and len(elements) < 16:
                if not words[2].isdigit() or len(words[2]) > 10 or int(words[2]) > 2**31 - 1:
                    raise ValueError
                # One element per name, so counts and properties describe the same one.
                if any(name == words[1] for name, _, _ in elements):
                    raise ValueError
                elements.append((words[1], int(words[2]), []))
            elif words[0] == "property" and elements and len(elements[-1][2]) < 256:
                if len(words) == 3 and words[1] in _PLY_TYPES:
                    elements[-1][2].append((words[2], words[1]))
                elif (
                    len(words) == 5
                    and words[1] == "list"
                    and words[2] in _PLY_TYPES
                    and words[3] in _PLY_TYPES
                ):
                    elements[-1][2].append((words[4], "list"))
                else:
                    raise ValueError
            else:
                raise ValueError
        if encoding is None:
            raise ValueError
    except ValueError:
        raise ModelPackageError("Malformed or unsupported PLY header") from None
    counts = {name: count for name, count, _ in elements}
    vertex = next((props for name, _, props in elements if name == "vertex"), [])
    types = dict(vertex)
    splat = (
        encoding == "binary_little_endian"
        and counts.get("vertex", 0) > 0
        and all(count == 0 for name, count, _ in elements if name != "vertex")
        and all(kind != "list" for _, kind in vertex)
        and all(types.get(name) in {"float", "float32"} for name in _SPLAT_PROPERTIES)
    )
    if splat and size is not None:
        stride = sum(_PLY_TYPES[kind] for _, kind in vertex)
        if size != header_bytes + counts["vertex"] * stride:
            raise ModelPackageError("PLY splat data does not match its header")
    return PlyHeader(
        UnitKind.SPLAT if splat else UnitKind.MESH,
        encoding,
        counts.get("vertex", 0),
        counts.get("face", 0),
        header_bytes,
        tuple(name for name, _ in vertex),
    )
