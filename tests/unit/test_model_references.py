# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""OBJ, MTL and glTF references resolve only to selected package members."""

import base64
import io
import json
import struct
import threading
from pathlib import Path

import pytest

from scenario.core.scene import model_references as refs
from scenario.core.scene.glb import MAX_ACCESSOR_ENTRIES, GLBError, inspect_glb
from scenario.core.scene.model_formats import ModelPackageError, PackageMember
from scenario.core.scene.model_references import (
    PackageCancelled,
    inspect_gltf_json,
    rewrite_mtl,
    rewrite_obj,
)

FIXTURE = Path(__file__).parents[1] / "fixtures/synthetic/static-triangle.glb"
UNSAFE = (b"/etc", b"..", b"https:", b"C:", b"\\\\server", b"delivered-")


def obj(text, material="material.mtl", cancel=None):
    target = io.BytesIO()
    result = rewrite_obj(io.BytesIO(text), target, material_name=material, cancel=cancel)
    assert result.bytes_written == len(target.getvalue())
    return result, target.getvalue()


def reasons(report):
    return [(item.line, item.keyword, item.reason) for item in report.dropped]


GEOMETRY = b"o Model\nv 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nusemtl Mat\ns off\nf 1/1 2/1 3/1\n"


@pytest.mark.parametrize(
    "library",
    [b"delivered-123.mtl", b"model.mtl", b"/etc/model.mtl", b"../../x.mtl", b"C:\\x y.mtl"],
)
def test_obj_material_library_points_only_at_the_snapshot(library):
    result, data = obj(b"# Exported\nmtllib " + library + b"\n" + GEOMETRY)
    assert data == b"# Exported\nmtllib material.mtl\n" + GEOMETRY
    assert result.material_linked and result.report.dropped_total == 0


def test_obj_without_a_bound_material_drops_every_library_and_file_statement():
    text = (
        b"mtllib a.mtl b.mtl\n"
        b"\tMTLLIB c.mtl\n"
        b"\x0cmtllib d.mtl\n"
        b"maplib maps.mpc\nusemap shiny\ncall other.obj\ncsh rm -rf x\n"
        b"shadow_obj s.obj\ntrace_obj t.obj\n" + GEOMETRY
    )
    result, data = obj(text, material=None)
    assert data == GEOMETRY and not result.material_linked
    assert reasons(result.report) == [
        (1, "mtllib", refs.MATERIAL_NOT_IN_PACKAGE),
        (2, "mtllib", refs.MATERIAL_NOT_IN_PACKAGE),
        (3, "mtllib", refs.MATERIAL_NOT_IN_PACKAGE),
        (4, "maplib", refs.UNSUPPORTED_REFERENCE),
        (5, "usemap", refs.UNSUPPORTED_REFERENCE),
        (6, "call", refs.UNSUPPORTED_REFERENCE),
        (7, "csh", refs.UNSUPPORTED_REFERENCE),
        (8, "shadow_obj", refs.UNSUPPORTED_REFERENCE),
        (9, "trace_obj", refs.UNSUPPORTED_REFERENCE),
    ]


def test_obj_keeps_one_library_and_copies_crlf_geometry_and_continuations():
    text = b"mtllib a.mtl\r\nmtllib b.mtl\r\nf 1 2 \\\r\n 3\r\nf 1 \\ \t\n2 3\nv 0 0 0"
    result, data = obj(text)
    assert data == b"mtllib material.mtl\nf 1 2 \\\r\n 3\r\nf 1 \\ \t\n2 3\nv 0 0 0"
    assert reasons(result.report) == [(2, "mtllib", refs.DUPLICATE_LIBRARY)]


@pytest.mark.parametrize(
    "text",
    [
        b"mtllib a.mtl \\\n b.mtl\n",
        b"mtllib a.mtl \\ \n b.mtl\n",
        b"mtllib\\\na.mtl\n",
        b"  \\\nmtllib a.mtl\n",
        b"call \\\n other.obj\n",
        b"v 0 0 0\0\n",
        b"v 0 0 0\rmtllib /x.mtl\n",
        b"v " + b"0" * refs.MAX_OBJ_LINE_BYTES + b"\n",
        b"f 1 2 \\\n" * (refs.MAX_OBJ_LINE_BYTES // 8 + 1),
    ],
    ids=[
        "continued-library",
        "continued-library-trailing-space",
        "continued-glued-keyword",
        "continued-keyword",
        "continued-call",
        "nul",
        "bare-cr",
        "long-line",
        "long-statement",
    ],
)
def test_obj_ambiguous_or_unbounded_text_fails_closed(text):
    with pytest.raises(ModelPackageError):
        obj(text)


@pytest.mark.parametrize(
    "keyword",
    [b"mtllib", b"MTLLIB", b"maplib", b"usemap", b"call", b"csh", b"shadow_obj", b"trace_obj"],
)
@pytest.mark.parametrize("ending", [b"\\\n", b"\\\r\n", b"\\ \n", b"\\\t\r\n"])
@pytest.mark.parametrize("statement", [b"v 0 0 0    ", b"f 1 2 3 ", b"# note "])
def test_a_reference_on_an_obj_continuation_line_fails_closed(statement, ending, keyword):
    # Blender 5.0 and 5.1 can read a continuation line by itself at a buffer boundary.
    text = GEOMETRY + statement + ending + keyword + b" ../outside.mtl\n" + GEOMETRY
    for material in ("material.mtl", None):
        with pytest.raises(ModelPackageError, match="continue across lines"):
            obj(text, material=material)


@pytest.mark.parametrize("name", ["../material.mtl", "/tmp/m.mtl", "Material.MTL", "m", ""])
def test_obj_snapshot_names_must_be_canonical(name):
    with pytest.raises(ValueError):
        obj(GEOMETRY, material=name)


def test_obj_rewrite_honors_cancellation():
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(PackageCancelled):
        obj(GEOMETRY, cancel=cancel)
    with pytest.raises(PackageCancelled):
        obj(b"v 0 0 0\n" * 65536, cancel=cancel)


def test_obj_rewrite_checks_cancellation_between_long_lines():
    cancel = threading.Event()
    cancel.set()
    line = b"v " + b"0" * (refs.MAX_OBJ_LINE_BYTES - 4) + b"\n"
    text, target = line * 6, io.BytesIO()
    with pytest.raises(PackageCancelled):
        rewrite_obj(io.BytesIO(text), target, cancel=cancel)
    # Stopped by bytes read, well before the end-of-file check.
    assert len(target.getvalue()) < refs.CANCEL_CHECK_BYTES < len(text)


TEXTURES = {"albedo": "texture-albedo.png", "normal": "texture-normal.png"}


def mtl(text, textures=TEXTURES):
    return rewrite_mtl(text, textures=textures)


def test_appended_maps_without_saved_files_are_dropped():
    text = (
        b"newmtl Material\nKd 1 1 1\n"
        b"map_Kd delivered-albedo.png\nmap_Pm delivered-metallic.png\n"
        b"map_Pr delivered-roughness.png\nmap_Bump -bm 0.5 delivered-normal.png\n"
    )
    result = mtl(text)
    assert result.data == (
        b"newmtl Material\nKd 1 1 1\n"
        b"map_Kd texture-albedo.png\nmap_Bump -bm 0.5 texture-normal.png\n"
    )
    assert result.bound == ("albedo", "normal")
    assert reasons(result.report) == [
        (4, "map_pm", refs.TEXTURE_NOT_IN_PACKAGE),
        (5, "map_pr", refs.TEXTURE_NOT_IN_PACKAGE),
    ]


def test_every_slot_keyword_maps_to_its_canonical_statement():
    names = {
        "albedo": "a.png",
        "normal": "n.png",
        "roughness": "r.jpg",
        "metallic": "m.webp",
    }
    for keyword, expected in [
        (b"map_Kd", b"map_Kd a.png"),
        (b"MAP_KD", b"map_Kd a.png"),
        (b"map_Pm", b"map_Pm m.webp"),
        (b"map_Pr", b"map_Pr r.jpg"),
        (b"map_Bump", b"map_Bump n.png"),
        (b"bump", b"map_Bump n.png"),
        (b"norm", b"map_Bump n.png"),
    ]:
        result = mtl(b"newmtl M\n" + keyword + b" /abs/t e x.png\n", names)
        assert result.data == b"newmtl M\n" + expected + b"\n"


def test_options_keep_only_numeric_scale_offset_and_bump_strength():
    text = (
        b"newmtl M\n"
        b"map_Kd -o 0.1 0.2 -s 2 -clamp on -mm 0 1 -blendu off -imfchan r -t 1 1 1 tex.png\n"
        b"map_Bump -bm 2 -bm 1e400 tex.png\n"
    )
    # A nonfinite or malformed option ends option parsing; later tokens are discarded.
    assert mtl(text).data == (
        b"newmtl M\nmap_Kd -o 0.1 0.2 -s 2 texture-albedo.png\nmap_Bump -bm 2 texture-normal.png\n"
    )
    text = b"newmtl N\nmap_Bump -bm nan -s 2 tex.png\n"
    assert mtl(text).data == b"newmtl N\nmap_Bump texture-normal.png\n"


@pytest.mark.parametrize(
    ("options", "kept"),
    [
        (b"-s 1_0", b""),
        (b"-bm 1e5_0", b""),
        (b"-o 1_0 0 0", b""),
        (b"-s 1 1_0", b"-s 1 "),
        (b"-s 0x1", b""),
        (b"-s 1e", b""),
        (b"-s 1.5e+", b""),
        (b"-s \xd9\xa1", b""),
        (b"-o 1. .5 -.5 -s +.5 1E-3 007", b"-o 1. .5 -.5 -s +.5 1E-3 007 "),
    ],
)
def test_option_values_are_plain_decimal_numbers(options, kept):
    # Blender rejects a value such as 1_0, which Python's float() accepts, and then
    # reads it as part of the file name.
    result = mtl(b"newmtl M\nmap_Kd " + options + b" provider/x.png\n")
    assert result.data == b"newmtl M\nmap_Kd " + kept + b"texture-albedo.png\n"


@pytest.mark.parametrize(
    "line",
    [
        b"map_Ks spec.png",
        b"map_d alpha.png",
        b"map_Ka ambient.png",
        b"map_Ke emissive.png",
        b"map_Kdx odd.png",
        b"refl -type sphere /etc/env.png",
        b"disp height.png",
        b"decal https://example.invalid/d.png",
        b"normal n.png",
        b"bumpy b.png",
    ],
)
def test_other_reference_statements_are_dropped(line):
    result = mtl(b"newmtl M\n" + line + b"\nNs 10\n")
    assert result.data == b"newmtl M\nNs 10\n" and result.bound == ()
    assert result.report.dropped[0].reason == refs.UNSUPPORTED_MAP


def test_different_files_for_one_slot_across_materials_are_ambiguous():
    text = b"newmtl A\nmap_Kd a.png\nmap_Bump n.png\nnewmtl B\nmap_Kd b.png\nmap_Bump n.png\n"
    result = mtl(text)
    assert result.data == (
        b"newmtl A\nmap_Bump texture-normal.png\nnewmtl B\nmap_Bump texture-normal.png\n"
    )
    assert result.bound == ("normal",)
    assert reasons(result.report) == [
        (2, "map_kd", refs.AMBIGUOUS_REFERENCE),
        (5, "map_kd", refs.AMBIGUOUS_REFERENCE),
    ]


def test_last_map_in_a_material_wins_and_blank_or_stray_maps_are_dropped():
    text = (
        b"map_Kd early.png\n"
        b"newmtl A\nmap_Kd first.png\nmap_Kd chosen.png\nmap_Kd\n"
        b"newmtl B\nmap_Kd   chosen.png\n"
    )
    result = mtl(text)
    assert result.data == (
        b"newmtl A\nmap_Kd texture-albedo.png\nnewmtl B\nmap_Kd texture-albedo.png\n"
    )
    assert reasons(result.report) == [
        (1, "map_kd", refs.OUTSIDE_MATERIAL),
        (3, "map_kd", refs.DUPLICATE_MAP),
        (5, "map_kd", refs.MISSING_REFERENCE),
    ]


def test_mtl_preserves_crlf_and_non_utf8_material_text():
    text = "newmtl Matériau\r\nKd 1 1 1\r\nmap_Kd C:\\tex.png\r\n".encode("latin-1")
    result = mtl(text)
    assert result.data == "newmtl Matériau\r\nKd 1 1 1\r\nmap_Kd texture-albedo.png\n".encode(
        "latin-1"
    )
    assert mtl(b"newmtl M\nKd 1 1 1").data == b"newmtl M\nKd 1 1 1\n"
    assert mtl(b"").data == b""


def test_mtl_output_never_contains_an_original_reference():
    hostile = [
        b"/etc/passwd",
        b"../../secret.png",
        b"https://example.invalid/x.png",
        b"C:\\Users\\x.png",
        b"\\\\server\\share\\x.png",
        b"delivered-albedo.png",
    ]
    text = b"newmtl M\n" + b"".join(b"map_Kd " + path + b"\nnewmtl M2\n" for path in hostile)
    data = mtl(text).data
    assert all(token not in data for token in UNSAFE)


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
@pytest.mark.parametrize(
    ("statement", "reference", "bound"),
    [
        (b"Ns 1 \\", b"map_Kd ../outside.png", ("albedo",)),
        (b"Kd 1 1 1\\", b"map_Kd /abs/outside.png", ("albedo",)),
        (b"Ns 1 \\ ", b"bump -bm 1 ../../outside.png", ("normal",)),
        (b"Kd 1 1 1 \\", b"refl -type sphere /etc/outside.png", ()),
        (b"Ns 1 \\", b"map_Ks ../outside.png", ()),
        (b"# note \\", b"map_Kd C:\\outside.png", ("albedo",)),
    ],
)
def test_a_trailing_backslash_never_hides_the_next_mtl_line(statement, reference, bound, newline):
    # Blender's MTL reader has no line continuation: it reads each line by itself.
    prefix = b"newmtl M" + newline + statement + newline
    result = mtl(prefix + reference + newline)
    assert result.bound == bound and result.report.dropped_total == (0 if bound else 1)
    assert result.data.startswith(prefix)
    assert all(token not in result.data for token in (*UNSAFE, b"outside", b"/abs"))


def test_reports_name_fixed_keywords_never_glued_reference_text():
    text = (
        b"newmtl M\n"
        b"map_Kd../../home/user/secret.png\n"
        b"refl\xa0https://cdn.example/x?sig=abc\n"
        b"MAP_KS spec.png\n"
        b"bumpy b.png\n"
        b"decal\x7fsecret.png\n"
    )
    result = rewrite_mtl(text, textures={})
    assert result.data == b"newmtl M\n"
    assert reasons(result.report) == [
        (2, "map_", refs.UNSUPPORTED_MAP),
        (3, "refl", refs.UNSUPPORTED_MAP),
        (4, "map_ks", refs.UNSUPPORTED_MAP),
        (5, "bump", refs.UNSUPPORTED_MAP),
        (6, "decal", refs.UNSUPPORTED_MAP),
    ]


@pytest.mark.parametrize(
    "text",
    [
        b"x" * (refs.MAX_MTL_BYTES + 1),
        b"newmtl M\nmap_Kd " + b"x" * refs.MAX_MTL_LINE_BYTES + b"\n",
        b"newmtl M\0\n",
        b"newmtl M\rmap_Kd /etc/x.png\n",
    ],
)
def test_mtl_size_line_and_byte_limits_fail_closed(text):
    with pytest.raises(ModelPackageError):
        mtl(text)


@pytest.mark.parametrize(
    "textures",
    [{"specular": "texture-specular.png"}, {"albedo": "../a.png"}, {"albedo": "A.PNG"}],
)
def test_mtl_texture_bindings_are_validated(textures):
    with pytest.raises(ValueError):
        mtl(b"newmtl M\n", textures)


def test_reports_are_bounded_but_count_every_dropped_reference():
    result = mtl(b"newmtl M\n" + b"map_Ks s.png\n" * 250)
    assert len(result.report.dropped) == refs.MAX_REPORTED_REFERENCES
    assert result.report.dropped_total == 250


def gltf_parts():
    data = FIXTURE.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20 : 20 + length])
    binary = data[28 + length :]
    return document, binary[: document["buffers"][0]["byteLength"]]


def external(buffer_uri="asset_buffer.bin", image_uri="textures/asset_image.png"):
    document, binary = gltf_parts()
    document["buffers"][0]["uri"] = buffer_uri
    if image_uri is not None:
        document["images"][0] = {"uri": image_uri}
    return document, binary


def encode(document):
    return json.dumps(document).encode()


def resources(binary, *extra):
    return (
        PackageMember("asset_buffer", "application/octet-stream", len(binary)),
        PackageMember("asset_image", "image/png", 70),
        *extra,
    )


def test_external_gltf_files_bind_to_package_members_by_identity():
    document, binary = external()
    result = inspect_gltf_json(encode(document), resources=resources(binary))
    rewritten = json.loads(result.document)
    assert rewritten["buffers"][0]["uri"] == "buffer-0.bin"
    assert rewritten["images"][0]["uri"] == "image-0.png"
    assert result.files == (("buffer-0.bin", "asset_buffer"), ("image-0.png", "asset_image"))
    assert result.data_uris == 0


def test_an_external_buffer_binds_by_unique_size_when_its_name_is_not_an_asset():
    document, binary = external(buffer_uri="scene%20data.bin", image_uri=None)
    other = PackageMember("asset_other", "application/octet-stream", len(binary) + 1)
    result = inspect_gltf_json(encode(document), resources=resources(binary, other))
    assert result.files == (("buffer-0.bin", "asset_buffer"),)
    twin = PackageMember("asset_twin", "application/octet-stream", len(binary))
    with pytest.raises(ModelPackageError, match="not part of the saved package"):
        inspect_gltf_json(encode(document), resources=resources(binary, twin))


def test_an_image_never_binds_through_a_buffer_uri():
    document, binary = external(image_uri="asset_buffer.bin")
    with pytest.raises(ModelPackageError, match="not part of the saved package"):
        inspect_gltf_json(encode(document), resources=resources(binary))
    # The same URI still binds the image member when one exists with that stem.
    image = PackageMember("asset_shared", "image/png", 70)
    buffer = PackageMember("asset_shared_bin", "application/octet-stream", len(binary))
    document, _ = external(buffer_uri="asset_shared.png", image_uri="asset_shared.png")
    result = inspect_gltf_json(encode(document), resources=(buffer, image))
    assert result.files == (("buffer-0.bin", "asset_shared_bin"), ("image-0.png", "asset_shared"))


def test_every_buffer_checks_its_own_length_even_for_a_repeated_uri():
    document, binary = external()
    document["buffers"].append({"uri": "asset_buffer.bin", "byteLength": len(binary) + 1000})
    with pytest.raises(ModelPackageError, match="size does not match"):
        inspect_gltf_json(encode(document), resources=resources(binary))
    document["buffers"][1]["byteLength"] = len(binary)
    rewritten = json.loads(
        inspect_gltf_json(encode(document), resources=resources(binary)).document
    )
    assert [buffer["uri"] for buffer in rewritten["buffers"]] == ["buffer-0.bin"] * 2


def test_data_uris_are_kept_and_checked():
    document, binary = gltf_parts()
    document["buffers"][0]["uri"] = (
        "data:application/octet-stream;base64," + base64.b64encode(binary).decode()
    )
    result = inspect_gltf_json(encode(document))
    assert result.files == () and result.data_uris == 1
    assert json.loads(result.document)["buffers"] == document["buffers"]
    document["buffers"][0]["byteLength"] += 1
    with pytest.raises(ModelPackageError, match="does not match"):
        inspect_gltf_json(encode(document))
    document, _ = gltf_parts()
    document["buffers"][0]["uri"] = "data:text/plain;base64,AAAA"
    with pytest.raises(ModelPackageError):
        inspect_gltf_json(encode(document))


def test_data_uris_accept_rfc_2397_parameters_before_base64():
    document, binary = gltf_parts()
    payload = base64.b64encode(binary).decode()
    document["buffers"][0]["uri"] = f"data:application/octet-stream;name=a.bin;base64,{payload}"
    document["images"][0] = {"uri": "data:image/png;charset=x;name=b.png;base64,iVBORw0K"}
    result = inspect_gltf_json(encode(document))
    assert result.files == () and result.data_uris == 2
    rewritten = json.loads(result.document)
    assert rewritten["buffers"] == document["buffers"]
    assert rewritten["images"] == document["images"]
    for header in (
        "image/png;name;base64",
        "image/png;=x;base64",
        "image/png;name=;base64",
        "image/png;base64;name=x",
        "image/png;name=x",
        "text/plain;name=x;base64",
    ):
        document["images"][0] = {"uri": f"data:{header},iVBORw0K"}
        with pytest.raises(ModelPackageError, match="base64 data URI"):
            inspect_gltf_json(encode(document))


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.invalid/asset_image.png",
        "file:///asset_image.png",
        "/asset_image.png",
        "../asset_image.png",
        "textures/../asset_image.png",
        "%2E%2E/asset_image.png",
        "C:/asset_image.png",
        "textures\\asset_image.png",
        "asset_image.png?x=1",
        "textures//asset_image.png",
        "asset_unknown.png",
        "asset_buffer.png",
    ],
)
def test_image_uris_outside_the_package_fail_closed(uri):
    document, binary = external(image_uri=uri)
    with pytest.raises(ModelPackageError):
        inspect_gltf_json(encode(document), resources=resources(binary))


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["buffers"][0].pop("uri"),
        lambda d: d["materials"][0].update(extensions={"X_audio": {"uri": "asset_image.png"}}),
        lambda d: d.update(animations=[{}]),
        lambda d: d["scenes"].append({"nodes": [0]}),
        lambda d: d.update(nodes=[]),
        lambda d: d["accessors"][0].update(count=0),
        lambda d: d["nodes"][0].update(matrix=[float("inf")] * 16),
        lambda d: d["asset"].update(version="1.0"),
        lambda d: d["buffers"][0].update(byteLength="134"),
        lambda d: d.update(buffers={}),
        lambda d: d.update(images=[{"uri": 7}]),
    ],
)
def test_gltf_document_policy_matches_the_glb_bounds(change):
    document, binary = external()
    change(document)
    with pytest.raises(ModelPackageError):
        inspect_gltf_json(
            encode(document).replace(b"Infinity", b"1e999"), resources=resources(binary)
        )


def test_animated_gltf_uses_the_bounded_new_group_policy():
    document, binary = external()
    document["animations"] = [{"channels": [{"target": {"node": 0, "path": "translation"}}]}]
    assert inspect_gltf_json(encode(document), resources=resources(binary), static_only=False)
    document["animations"][0]["channels"][0]["target"]["path"] = "pointer"
    with pytest.raises(ModelPackageError, match="morph-weight"):
        inspect_gltf_json(encode(document), resources=resources(binary), static_only=False)


def pack_glb(document, binary):
    text = json.dumps(document).encode()
    text += b" " * (-len(text) % 4)
    body = binary + b"\0" * (-len(binary) % 4)
    size = 28 + len(text) + len(body)
    return b"".join(
        [
            struct.pack("<4sII", b"glTF", 2, size),
            struct.pack("<I4s", len(text), b"JSON"),
            text,
            struct.pack("<I4s", len(body), b"BIN\0"),
            body,
        ]
    )


def channel(path="translation", node=0):
    return {"channels": [{"target": {"node": node, "path": path}}]}


@pytest.mark.parametrize("static_only", [True, False])
@pytest.mark.parametrize(
    "change",
    [
        lambda d: None,
        lambda d: d["asset"].update(version="1.0"),
        lambda d: d.update(animations=[channel()]),
        lambda d: d.update(skins=[{"joints": [0]}]),
        lambda d: d.update(skins=[{"joints": [9]}]),
        lambda d: d.update(animations=[channel("pointer")]),
        lambda d: d.update(animations=[channel(node=9)]),
        lambda d: d.update(animations=[channel()] * 129),
        lambda d: d["scenes"].append({"nodes": [0]}),
        lambda d: d.update(scene=1),
        lambda d: d.update(nodes=[]),
        lambda d: d.update(nodes=d["nodes"] * 10_001),
        lambda d: d["accessors"][0].update(count=0),
        lambda d: d["accessors"][0].update(count="3"),
        lambda d: d["accessors"][0].update(count=MAX_ACCESSOR_ENTRIES + 1),
    ],
)
def test_gltf_document_checks_stay_aligned_with_inspect_glb(change, static_only):
    """The JSON glTF policy duplicates GLB document checks; they must not drift."""
    embedded, binary = gltf_parts()
    external_document, _ = external(image_uri=None)
    change(embedded)
    change(external_document)
    outcomes = []
    for check in (
        lambda: inspect_glb(pack_glb(embedded, binary), static_only=static_only),
        lambda: inspect_gltf_json(
            encode(external_document), resources=resources(binary), static_only=static_only
        ),
    ):
        try:
            check()
            outcomes.append(True)
        except (GLBError, ModelPackageError):
            outcomes.append(False)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    "data",
    [
        b"\xef\xbb\xbf{}",
        b"{",
        b"[]",
        b'{"asset": {"version": "2.0"}, "x": NaN}',
        b" " * (refs.MAX_GLTF_JSON_BYTES + 1),
    ],
)
def test_malformed_gltf_text_fails_closed(data):
    with pytest.raises(ModelPackageError):
        inspect_gltf_json(data)


def test_gltf_resource_sizes_and_types_are_bounded():
    document, binary = external()
    unknown = (
        PackageMember("asset_buffer", "application/octet-stream", None),
        PackageMember("asset_image", "image/png", 70),
    )
    with pytest.raises(ModelPackageError):
        inspect_gltf_json(encode(document), resources=unknown)
    huge = (
        PackageMember("asset_buffer", "application/octet-stream", len(binary)),
        PackageMember("asset_image", "image/png", 256 * 1024 * 1024),
        PackageMember("asset_image2", "image/png", 256 * 1024 * 1024),
    )
    document["images"].append({"uri": "asset_image2.png"})
    with pytest.raises(ModelPackageError, match="exceeds"):
        inspect_gltf_json(encode(document), resources=huge)
    mismatched = (
        PackageMember("asset_buffer", "application/octet-stream", len(binary) + 4),
        PackageMember("asset_image", "image/png", 70),
    )
    with pytest.raises(ModelPackageError, match="size does not match"):
        inspect_gltf_json(encode(external()[0]), resources=mismatched)
    with pytest.raises(ValueError):
        inspect_gltf_json(encode(document), resources=["asset_buffer"])
