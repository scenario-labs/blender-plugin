# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rewrite saved OBJ, MTL and glTF references to private snapshot names. No bpy.

Every external reference either resolves to a member of the selected import unit
under a canonical snapshot name or is removed (OBJ/MTL) or rejected (glTF).
Provider names, absolute paths, traversal and URLs never reach an importer. The
importer's own file search stays inside the snapshot only if the caller writes
every canonical name passed here into the snapshot before import: Blender looks
for a missing file elsewhere, including the process working directory. The import
must still check the images it creates. Every physical line is classified on its
own: Blender's MTL reader has no line continuation, and Blender 5.0 and 5.1 can
read an OBJ continuation line by itself at a read-buffer boundary. Functions take
and return bytes or binary streams, so a worker can run them on verified copies.
"""

import base64
import binascii
import io
import json
import math
import re
from dataclasses import dataclass
from urllib.parse import unquote

from .glb import MAX_ACCESSOR_ENTRIES, GLBError, _check_animation_bounds
from .model_formats import (
    BUFFER_MEDIA_TYPES,
    MAX_GLTF_JSON_BYTES,
    MAX_MEMBER_BYTES,
    MAX_MTL_BYTES,
    MAX_PACKAGE_BYTES,
    TEXTURE_EXTENSIONS,
    TEXTURE_SLOTS,
    ModelPackageError,
    PackageMember,
)

MAX_OBJ_LINE_BYTES = 1024 * 1024
MAX_MTL_LINE_BYTES = 64 * 1024
MAX_REPORTED_REFERENCES = 100
MAX_GLTF_FILES = 256
# Streaming checks cancellation at least this often, whatever the line length.
CANCEL_CHECK_BYTES = 4 * 1024 * 1024

# Reasons for dropped OBJ/MTL statements.
MATERIAL_NOT_IN_PACKAGE = "material-not-in-package"
DUPLICATE_LIBRARY = "duplicate-library"
UNSUPPORTED_REFERENCE = "unsupported-reference"
TEXTURE_NOT_IN_PACKAGE = "texture-not-in-package"
AMBIGUOUS_REFERENCE = "ambiguous-reference"
DUPLICATE_MAP = "duplicate-map"
OUTSIDE_MATERIAL = "outside-material"
UNSUPPORTED_MAP = "unsupported-map"
MISSING_REFERENCE = "missing-reference"


class PackageCancelled(RuntimeError):
    """Preparation stopped before producing a snapshot file."""


@dataclass(frozen=True)
class DroppedReference:
    """One removed statement; the original reference text is never retained.

    ``keyword`` is a fixed lowercase statement name. An unknown keyword reports only
    its matched prefix, such as ``map_``, because a reference may be glued to it.
    """

    line: int
    keyword: str
    reason: str


@dataclass(frozen=True)
class ReferenceReport:
    dropped: tuple[DroppedReference, ...]
    dropped_total: int


_OBJ_DROPPED = frozenset({b"maplib", b"usemap", b"call", b"csh", b"shadow_obj", b"trace_obj"})
_OBJ_REFERENCES = _OBJ_DROPPED | {b"mtllib"}
# Statements a prefix-matching reader could treat as texture references.
_REFERENCE_PREFIXES = (b"map_", b"refl", b"bump", b"norm", b"disp", b"decal")
# MTL texture statements reported by name.
_MTL_REFERENCES = frozenset(
    {
        b"map_ka",
        b"map_kd",
        b"map_ks",
        b"map_ke",
        b"map_ns",
        b"map_d",
        b"map_tr",
        b"map_aat",
        b"map_bump",
        b"map_refl",
        b"map_pr",
        b"map_pm",
        b"map_ps",
        b"map_pc",
        b"map_pcr",
        b"bump",
        b"norm",
        b"disp",
        b"decal",
        b"refl",
    }
)


def _reported_keyword(keyword):
    if keyword in _OBJ_REFERENCES or keyword in _MTL_REFERENCES:
        return keyword.decode("ascii")
    prefix = next((p for p in _REFERENCE_PREFIXES if keyword.startswith(p)), b"reference")
    return prefix.decode("ascii")


class _Report:
    def __init__(self):
        self.dropped, self.total = [], 0

    def drop(self, line, keyword, reason):
        self.total += 1
        if len(self.dropped) < MAX_REPORTED_REFERENCES:
            self.dropped.append(DroppedReference(line, _reported_keyword(keyword), reason))

    def freeze(self):
        return ReferenceReport(tuple(self.dropped), self.total)


def _snapshot_name(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]{0,63}\.[a-z0-9]{1,8}", value
    ):
        raise ValueError("Use a canonical snapshot file name")
    return value.encode("ascii")


# Lines end at LF. Every byte up to space separates tokens, so a reader that
# treats any control byte as whitespace cannot find a keyword that this
# classification missed.
_CONTROL = bytes(range(33))
_SPACES = bytes.maketrans(_CONTROL, b" " * len(_CONTROL))


def _tokens(text):
    return text.translate(_SPACES).split()


def _keyword(line):
    """Lowercase first token of one physical line."""
    words = _tokens(line)
    return words[0].lower() if words else b""


def _obj_continued(line):
    """Blender continues an OBJ statement after a backslash and optional whitespace."""
    return line.endswith(b"\n") and line[:-1].rstrip(_CONTROL).endswith(b"\\")


def _obj_keyword(line):
    """Lowercase first token of a physical OBJ line that could read a file, else b"".

    Geometry statements start with other letters. Blender turns a continuation
    backslash into a space, so it never extends the keyword.
    """
    head = line.lstrip(_CONTROL)[:1].lower()
    if not head or head not in b"mcstu":
        return b""
    if _obj_continued(line):
        line = line[:-1].rstrip(_CONTROL)[:-1]
    return _keyword(line)


def _lines(read, limit, cancel, continued=None):
    """Yield (first physical line number, physical lines) for each statement.

    Without ``continued`` every physical line is its own statement. A carriage
    return is accepted only before a line feed: a reader that also splits lines at
    a bare CR could otherwise see a statement this one copied. Cancellation is
    checked every 65,536 lines and every ``CANCEL_CHECK_BYTES``.
    """
    number, lines, size, start, total = 0, [], 0, 1, 0
    checkpoint = CANCEL_CHECK_BYTES
    while True:
        line = read(limit + 1)
        if not line:
            break
        number += 1
        size += len(line)
        total += len(line)
        if cancel is not None and (number % 65536 == 0 or total >= checkpoint):
            checkpoint = total + CANCEL_CHECK_BYTES
            if cancel.is_set():
                raise PackageCancelled("Model package preparation cancelled")
        if size > limit or total > MAX_MEMBER_BYTES:
            raise ModelPackageError("A model package line or file exceeds the supported limit")
        body = line[:-2] if line.endswith(b"\r\n") else line.rstrip(b"\n")
        if b"\0" in body or b"\r" in body:
            raise ModelPackageError("Use model package text with LF or CRLF line endings")
        lines.append(line)
        if continued is None or not continued(line):
            yield start, lines
            lines, size, start = [], 0, number + 1
    if lines:
        yield start, lines


@dataclass(frozen=True)
class ObjRewrite:
    report: ReferenceReport
    material_linked: bool
    bytes_written: int


def rewrite_obj(source, target, *, material_name=None, cancel=None):
    """Stream an OBJ, pointing its first ``mtllib`` at ``material_name`` or dropping it.

    Other ``mtllib`` statements and file-reading statements (``maplib``, ``usemap``,
    ``call``, ``csh``, ``shadow_obj``, ``trace_obj``) are removed. Other statements,
    including continued geometry, are copied unchanged. A continued statement is
    rejected when any of its physical lines starts with one of these keywords:
    removing it could change how the importer reads the next statement, and
    Blender 5.0 and 5.1 can read a continuation line by itself.
    """
    material = _snapshot_name(material_name) if material_name is not None else None
    report, linked, written = _Report(), False, 0
    for number, lines in _lines(source.readline, MAX_OBJ_LINE_BYTES, cancel, _obj_continued):
        keyword = _obj_keyword(lines[0])
        if len(lines) > 1 and any(_obj_keyword(line) in _OBJ_REFERENCES for line in lines):
            raise ModelPackageError("OBJ file references cannot continue across lines")
        if keyword in _OBJ_REFERENCES:
            if keyword != b"mtllib":
                report.drop(number, keyword, UNSUPPORTED_REFERENCE)
                continue
            if material is None:
                report.drop(number, keyword, MATERIAL_NOT_IN_PACKAGE)
                continue
            if linked:
                report.drop(number, keyword, DUPLICATE_LIBRARY)
                continue
            linked, lines = True, [b"mtllib " + material + b"\n"]
        for line in lines:
            target.write(line)
            written += len(line)
    if cancel is not None and cancel.is_set():
        raise PackageCancelled("Model package preparation cancelled")
    return ObjRewrite(report.freeze(), linked, written)


_MAP_SLOTS = {
    b"map_kd": "albedo",
    b"map_pm": "metallic",
    b"map_pr": "roughness",
    b"map_bump": "normal",
    b"bump": "normal",
    b"norm": "normal",
}
_CANONICAL_MAP = {
    "albedo": b"map_Kd",
    "metallic": b"map_Pm",
    "roughness": b"map_Pr",
    "normal": b"map_Bump",
}
# Option arities from the MTL texture statement grammar; only numeric
# scale/offset and bump multiplier options are retained.
_OPTION_ARITY = {
    b"-bm": (1, 1),
    b"-o": (1, 3),
    b"-s": (1, 3),
    b"-t": (1, 3),
    b"-mm": (2, 2),
    b"-clamp": (1, 1),
    b"-blendu": (1, 1),
    b"-blendv": (1, 1),
    b"-cc": (1, 1),
    b"-boost": (1, 1),
    b"-texres": (1, 1),
    b"-imfchan": (1, 1),
    b"-type": (1, 1),
}
_KEPT_OPTIONS = frozenset({b"-bm", b"-o", b"-s"})
_WORD_OPTIONS = frozenset({b"-clamp", b"-blendu", b"-blendv", b"-cc", b"-imfchan", b"-type"})
# Plain ASCII decimal notation only. Blender keeps an option value only when the
# whole token is one number; it rejects forms Python's float() accepts, such as
# digit-group underscores, and then reads the token as part of the file name.
_NUMBER = re.compile(rb"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def _number(token):
    return _NUMBER.fullmatch(token) is not None and math.isfinite(float(token))


def _map_statement(statement):
    """Return (kept option tokens, normalized original reference) of a map line.

    The reference is compared between materials and then discarded; it never
    becomes a path.
    """
    words = _tokens(statement)[1:]
    kept, index = [], 0
    # Leave at least one token for the file reference.
    while index < len(words) - 1 and words[index].lower() in _OPTION_ARITY:
        option = words[index].lower()
        low, high = _OPTION_ARITY[option]
        end = index + 1
        while (
            end - index - 1 < high
            and end < len(words) - 1
            and (option in _WORD_OPTIONS or _number(words[end]))
        ):
            end += 1
        if end - index - 1 < low:
            break
        if option in _KEPT_OPTIONS:
            kept += [option, *words[index + 1 : end]]
        index = end
    return kept, b" ".join(words[index:])


@dataclass(frozen=True)
class MtlRewrite:
    data: bytes
    report: ReferenceReport
    bound: tuple[str, ...]


def rewrite_mtl(data, *, textures):
    """Point supported MTL maps at bound snapshot textures; drop every other map.

    ``textures`` maps slots (albedo, normal, roughness, metallic) to snapshot names.
    ``map_Kd``, ``map_Pm``, ``map_Pr`` and ``map_Bump``/``bump``/``norm`` statements
    bind by slot. Within one material the last statement for a slot wins. If
    materials name different files for one slot, that slot is ambiguous and all its
    statements are dropped rather than sharing one texture. Other map, ``refl``,
    ``disp`` and ``decal`` statements are dropped. Blender's MTL reader has no line
    continuation, so each physical line is classified and a trailing backslash
    never hides the next one.
    """
    names = {}
    for slot, name in dict(textures).items():
        if slot not in TEXTURE_SLOTS:
            raise ValueError("Use a supported material texture slot")
        names[slot] = _snapshot_name(name)
    data = bytes(data)
    if len(data) > MAX_MTL_BYTES:
        raise ModelPackageError("Material library exceeds the supported import limit")
    statements = [
        (number, line, _keyword(line))
        for number, (line,) in _lines(io.BytesIO(data).readline, MAX_MTL_LINE_BYTES, None)
    ]
    # First pass: the last statement naming a file per (material, slot).
    material, effective, references = None, {}, {}
    for position, (_, statement, keyword) in enumerate(statements):
        if keyword == b"newmtl":
            material = position
        elif keyword in _MAP_SLOTS and material is not None:
            reference = _map_statement(statement)[1]
            if reference:
                effective[(material, _MAP_SLOTS[keyword])] = position, reference
    for (_, slot), (_, reference) in effective.items():
        references.setdefault(slot, set()).add(reference)
    ambiguous = {slot for slot, values in references.items() if len(values) > 1}
    effective = {key: position for key, (position, _) in effective.items()}
    report, output, bound, material = _Report(), [], set(), None
    for position, (number, statement, keyword) in enumerate(statements):
        if keyword == b"newmtl":
            material = position
        if not keyword.startswith(_REFERENCE_PREFIXES):
            output.append(statement)
            continue
        slot = _MAP_SLOTS.get(keyword)
        kept, reference = _map_statement(statement) if slot else ([], b"")
        if slot is None:
            report.drop(number, keyword, UNSUPPORTED_MAP)
        elif material is None:
            report.drop(number, keyword, OUTSIDE_MATERIAL)
        elif not reference:
            report.drop(number, keyword, MISSING_REFERENCE)
        elif slot not in names:
            report.drop(number, keyword, TEXTURE_NOT_IN_PACKAGE)
        elif slot in ambiguous:
            report.drop(number, keyword, AMBIGUOUS_REFERENCE)
        elif effective.get((material, slot)) != position:
            report.drop(number, keyword, DUPLICATE_MAP)
        else:
            bound.add(slot)
            output.append(b" ".join([_CANONICAL_MAP[slot], *kept, names[slot]]) + b"\n")
    text = b"".join(output)
    if text and not text.endswith(b"\n"):
        text += b"\n"
    return MtlRewrite(text, report.freeze(), tuple(s for s in TEXTURE_SLOTS if s in bound))


@dataclass(frozen=True)
class GltfPackage:
    """A rewritten glTF document and the package members it reads."""

    document: bytes
    files: tuple[tuple[str, str], ...]
    data_uris: int


def _reject_constant(_value):
    raise ModelPackageError("Nonfinite JSON values are unsupported")


def _relative_stem(uri):
    """Return the file stem of a plain relative URI, or None for any other form."""
    if (
        not uri
        or not uri.isascii()
        or any(ord(char) < 32 or char in "\\?#" for char in uri)
        or uri.startswith("/")
        or ":" in uri.split("/", 1)[0]
    ):
        return None
    try:
        path = unquote(uri, errors="strict")
    except UnicodeDecodeError:
        return None
    parts = path.split("/")
    if any(part in {"", ".", ".."} or any(c in part for c in "\\:\0") for part in parts):
        return None
    return parts[-1].rsplit(".", 1)[0]


def _data_uri(uri, media_types):
    """Decode a base64 data URI with an allowed media type, or raise."""
    header, separator, payload = uri[5:].partition(",")
    media, _, encoding = header.partition(";")
    if not separator or encoding != "base64" or media not in media_types:
        raise ModelPackageError("Use a base64 data URI with a supported media type")
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ModelPackageError("Malformed glTF data URI") from None


def _walk(value, allowed):
    pending = [value]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if "uri" in value and id(value) not in allowed:
                raise ModelPackageError("glTF references files outside buffers and images")
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ModelPackageError("Nonfinite glTF values are unsupported")


def _check_document(document, static_only):
    """Apply the GLB document bounds of glb.inspect_glb to a JSON glTF."""
    if document["asset"]["version"] != "2.0":
        raise ModelPackageError("Use glTF 2.0")
    if static_only and (document.get("animations") or document.get("skins")):
        raise ModelPackageError("Rigged or animated results require their own application policy")
    if len(document.get("scenes", [])) != 1 or document.get("scene", 0) != 0:
        raise ModelPackageError("Choose a glTF with one model scene")
    if not 0 < len(document.get("nodes", [])) <= 10_000:
        raise ModelPackageError("glTF node count exceeds the supported import limit")
    if not static_only:
        try:
            _check_animation_bounds(document)
        except GLBError as error:
            raise ModelPackageError(str(error).replace("GLB", "glTF")) from None
    counts = [accessor["count"] for accessor in document.get("accessors", [])]
    if any(type(value) is not int or value < 1 for value in counts):
        raise ModelPackageError("Invalid accessor count")
    if sum(counts) > MAX_ACCESSOR_ENTRIES:
        raise ModelPackageError("glTF geometry exceeds the synchronous import limit")


class _Resources:
    """Bind external glTF URIs only to members of the selected unit."""

    def __init__(self, resources):
        self.members = tuple(resources)
        if not all(isinstance(member, PackageMember) for member in self.members):
            raise ValueError("Use package members as glTF resources")
        self.by_uri, self.names, self.counts = {}, {}, {"buffer": 0, "image": 0}

    def _match(self, uri, kind, byte_length):
        stem = _relative_stem(uri)
        if stem is None:
            raise ModelPackageError("glTF references a path or URL outside the saved package")
        types = BUFFER_MEDIA_TYPES if kind == "buffer" else TEXTURE_EXTENSIONS
        candidates = [m for m in self.members if m.media_type in types]
        matches = [m for m in candidates if m.asset_id == stem]
        if not matches and kind == "buffer":
            bound = {member.asset_id for member in self.names}
            matches = [m for m in candidates if m.size == byte_length and m.asset_id not in bound]
        if len(matches) != 1:
            raise ModelPackageError("glTF references a file that is not part of the saved package")
        return matches[0]

    def bind(self, uri, kind, byte_length=None):
        # Keyed by kind and URI, and every buffer checks its own length, so a repeated
        # URI never skips the media type or size check of the entry that binds it.
        key = (kind, uri)
        member = self.by_uri[key] if key in self.by_uri else self._match(uri, kind, byte_length)
        if member.size is None or member.size > MAX_MEMBER_BYTES:
            raise ModelPackageError("glTF resource size is unknown or exceeds the import limit")
        if kind == "buffer" and member.size != byte_length:
            raise ModelPackageError("The glTF buffer size does not match its saved file")
        if member not in self.names:
            if len(self.names) >= MAX_GLTF_FILES:
                raise ModelPackageError("glTF references too many files")
            number = self.counts[kind]
            self.counts[kind] += 1
            suffix = "bin" if kind == "buffer" else TEXTURE_EXTENSIONS[member.media_type]
            self.names[member] = f"{kind}-{number}.{suffix}"
        self.by_uri[key] = member
        return self.names[member]


def inspect_gltf_json(data, *, resources=(), static_only=True):
    """Validate a JSON glTF and bind its URIs to the selected package members.

    Bounds match the GLB preflight (one scene, node, accessor and animation limits).
    Base64 data URIs are kept. An external buffer binds to the resource whose asset
    ID equals the URI's file stem, else to the only unbound octet-stream resource
    whose size equals ``byteLength``. An external image binds only by asset ID stem.
    Any other URI, including those in extensions, fails closed. Returns the
    rewritten document and the (snapshot name, asset ID) files it reads.
    """
    data = bytes(data)
    if len(data) > MAX_GLTF_JSON_BYTES:
        raise ModelPackageError("glTF description exceeds the supported import limit")
    binder = _Resources(resources)
    try:
        document = json.loads(data.decode("utf-8"), parse_constant=_reject_constant)
        _check_document(document, static_only)
        buffers, images = document["buffers"], document.get("images", [])
        if not isinstance(buffers, list) or not isinstance(images, list):
            raise ModelPackageError("Malformed glTF buffer or image list")
        if not 0 < len(buffers) <= MAX_GLTF_FILES or len(images) > MAX_GLTF_FILES:
            raise ModelPackageError("glTF buffer or image count exceeds the import limit")
        allowed = {id(entry) for entry in buffers + images}
        _walk(document, allowed)
        inline = 0
        for buffer in buffers:
            length, uri = buffer["byteLength"], buffer.get("uri")
            if type(length) is not int or not 0 < length <= MAX_MEMBER_BYTES:
                raise ModelPackageError("Invalid glTF buffer length")
            if not isinstance(uri, str):
                raise ModelPackageError("Use a glTF buffer URI")
            if uri.startswith("data:"):
                if len(_data_uri(uri, BUFFER_MEDIA_TYPES)) != length:
                    raise ModelPackageError("A glTF data buffer does not match its length")
                inline += 1
            else:
                buffer["uri"] = binder.bind(uri, "buffer", length)
        for image in images:
            uri = image.get("uri")
            if uri is None:
                continue
            if not isinstance(uri, str):
                raise ModelPackageError("Use a glTF image URI")
            if uri.startswith("data:"):
                if not _data_uri(uri, TEXTURE_EXTENSIONS):
                    raise ModelPackageError("A glTF data image is empty")
                inline += 1
            else:
                image["uri"] = binder.bind(uri, "image")
        total = len(data) + sum(member.size for member in binder.names)
        if total > MAX_PACKAGE_BYTES:
            raise ModelPackageError("glTF package exceeds the supported import limit")
        rewritten = json.dumps(document, separators=(",", ":"), allow_nan=False).encode()
    except ModelPackageError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        raise ModelPackageError("Malformed or unsupported glTF description") from None
    files = tuple(sorted((name, member.asset_id) for member, name in binder.names.items()))
    return GltfPackage(rewritten, files, inline)
