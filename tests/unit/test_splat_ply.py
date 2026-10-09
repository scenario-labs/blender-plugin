# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""3DGS PLY classification and bounded strided decoding, independent of Blender."""

import io
import math

import pytest
from splat_files import SPLAT_PROPERTIES, ply_bytes, splat_row

from scenario.core.scene import splat_ply, splats
from scenario.core.scene.splats import SplatError, SplatOptions

SPLAT = [(name, "float") for name in SPLAT_PROPERTIES]
XYZ = [("x", "float"), ("y", "float"), ("z", "float")]
OPENCV = SplatOptions(1000, "OPENCV")
# Real 3DGS exports interleave normals, higher SH and rotations with the needed columns.
EXPORT = (
    [("x", "float"), ("y", "float"), ("z", "float")]
    + [(name, "float") for name in ("nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2")]
    + [(f"f_rest_{i}", "float") for i in range(9)]
    + [("opacity", "float"), ("flags", "uchar"), ("weight", "double")]
    + [(f"scale_{i}", "float") for i in range(3)]
    + [(f"rot_{i}", "float") for i in range(4)]
)


def header(data):
    reader = splats.Reader(io.BytesIO(data))
    return splat_ply.read_header(reader), reader


def decode(data, options=OPENCV, **kwargs):
    parsed, reader = header(data)
    return splat_ply.decode(reader, parsed, options=options, size=len(data), **kwargs)


def triples(values, width=3):
    values = values.tolist()
    return [tuple(values[i : i + width]) for i in range(0, len(values), width)]


@pytest.mark.parametrize("properties", [SPLAT, EXPORT])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_binary_little_endian_gaussian_rows_are_splats(properties, newline):
    data = ply_bytes([splat_row(0)], properties=properties, newline=newline)
    parsed, reader = header(data)
    assert parsed.splat and parsed.format == "binary_little_endian"
    assert parsed.classify() == "splat"
    assert parsed.length == data.index(b"end_header") + len(b"end_header") + len(newline)
    assert reader.read(4) == data[parsed.length : parsed.length + 4]


@pytest.mark.parametrize(
    "build",
    [
        lambda: ply_bytes([{"x": 1.0}], properties=XYZ),
        lambda: ply_bytes(
            [{"x": 1.0}], properties=[("x", "double"), ("y", "double"), ("z", "double")]
        ),
        lambda: ply_bytes([{}], properties=[*XYZ, ("red", "uchar")], fmt="ascii"),
        lambda: ply_bytes(
            [{}],
            properties=XYZ,
            fmt="binary_big_endian",
            elements=[("face", 1, ["property list uchar int vertex_indices"])],
        ),
    ],
)
def test_vertex_meshes_and_point_clouds_are_classified_as_meshes(build):
    parsed, _ = header(build())
    assert not parsed.splat and parsed.classify() == "mesh"
    with pytest.raises(SplatError, match="no Gaussian splat"):
        splat_ply.decode(splats.Reader(io.BytesIO(b"")), parsed, options=SplatOptions(1, "OPENGL"))


@pytest.mark.parametrize(
    "build",
    [
        lambda: ply_bytes([splat_row(0)], fmt="ascii"),
        lambda: ply_bytes([splat_row(0)], fmt="binary_big_endian"),
        lambda: ply_bytes([splat_row(0)], properties=SPLAT[:-1]),
        lambda: ply_bytes([splat_row(0)], properties=[("x", "double"), *SPLAT[1:]]),
        lambda: ply_bytes([splat_row(0)], properties=[(name, "double") for name, _ in EXPORT]),
        lambda: ply_bytes(
            [splat_row(0)], elements=[("face", 1, ["property list uchar int vertex_indices"])]
        ),
        lambda: ply_bytes([], properties=SPLAT),
        lambda: (
            b"ply\nformat binary_little_endian 1.0\nelement vertex 1\n"
            + b"".join(f"property float {name}\n".encode() for name, _ in SPLAT)
            + b"property list uchar float extra\nend_header\n"
        ),
    ],
)
def test_gaussian_layouts_this_decoder_cannot_read_fail_closed(build):
    parsed, _ = header(build())
    assert not parsed.splat
    with pytest.raises(SplatError, match="Gaussian splat PLY layout.*saved file is kept"):
        parsed.classify()


def test_compressed_splat_ply_is_rejected_explicitly():
    data = (
        b"ply\nformat binary_little_endian 1.0\nelement chunk 1\n"
        + b"".join(f"property float {name}\n".encode() for name in ("min_x", "max_x"))
        + b"element vertex 256\n"
        + b"".join(
            f"property uint packed_{name}\n".encode()
            for name in ("position", "rotation", "scale", "color")
        )
        + b"end_header\n"
    )
    with pytest.raises(SplatError, match="Compressed splat PLY.*saved file is kept"):
        header(data)[0].classify()


@pytest.mark.parametrize(
    "build",
    [
        lambda: ply_bytes([], properties=XYZ),
        lambda: ply_bytes([{}], properties=XYZ[:2]),
        lambda: ply_bytes([{}], properties=[("u", "float"), ("v", "float")]),
        lambda: (
            b"ply\nformat binary_little_endian 1.0\nelement face 0\n"
            b"property list uchar int vertex_indices\nelement vertex 1\n"
            b"property float x\nproperty float y\nproperty float z\nend_header\n"
        ),
        lambda: (
            b"ply\nformat ascii 1.0\nelement point 1\n"
            b"property float x\nproperty float y\nproperty float z\nend_header\n"
        ),
        lambda: (
            b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\n"
            b"property list uchar float z\nend_header\n"
        ),
    ],
)
def test_other_layouts_are_neither_splats_nor_meshes(build):
    parsed, _ = header(build())
    with pytest.raises(SplatError, match="Unsupported PLY layout; the saved file is kept"):
        parsed.classify()


def test_empty_face_element_does_not_make_a_mesh():
    data = ply_bytes(
        [splat_row(0)], elements=[("face", 0, ["property list uchar int vertex_indices"])]
    )
    assert header(data)[0].splat


@pytest.mark.parametrize(
    "data, message",
    [
        (b"", "incomplete"),
        (b"ply\nformat binary_little_endian 1.0\nelement vertex 1\n", "incomplete"),
        (b"plyx\nend_header\n", "Not a PLY"),
        (b"ply\nelement vertex 1\nproperty float x\nend_header\n", "no format"),
        (b"ply\nformat binary_little_endian 1.0\nend_header\n", "no format or elements"),
        (b"ply\nformat binary_little_endian 2.0\nend_header\n", "format"),
        (b"ply\nformat binary_little_endian 1.0\nproperty float x\nend_header\n", "header line"),
        (b"ply\nformat ascii 1.0\nelement vertex -1\nend_header\n", "header line"),
        (b"ply\nformat ascii 1.0\nelement vertex 99999999999\nend_header\n", "header line"),
        (b"ply\nformat ascii 1.0\nelement vertex 4294967295\nend_header\n", "element"),
        (b"ply\nformat ascii 1.0\nelement vertex 1\nproperty half x\nend_header\n", "property"),
        (
            b"ply\nformat ascii 1.0\nelement vertex 1\nproperty list float int i\nend_header\n",
            "property",
        ),
        (
            b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty int x\n"
            b"end_header\n",
            "name",
        ),
        (b"ply\nformat ascii 1.0\ncomment \xff\nend_header\n", "ASCII"),
        (b"ply\nformat ascii 1.0\nformat ascii 1.0\nend_header\n", "header line"),
        (b"ply\n" + b"comment " + b"x" * 70000 + b"\nend_header\n", "64 KiB"),
    ],
)
def test_malformed_headers_fail_closed(data, message):
    with pytest.raises(SplatError, match=message):
        header(data)


def test_activations_offsets_and_opencv_axes():
    rows = [splat_row(i) for i in range(3)]
    for index, row in enumerate(rows):
        row.update(nx=9.0, f_rest_0=7.0, flags=255, weight=-3.5, rot_0=1.0)
        row["opacity"] = (0.0, 2.0, -200.0)[index]
    data = decode(ply_bytes(rows, properties=EXPORT))
    assert (data.format, data.version, data.count, data.kept, data.step) == ("ply", None, 3, 3, 1)
    # OPENCV saved (x, y, z) becomes Blender (x, z, -y).
    assert triples(data.floats("positions")) == [(row["x"], row["z"], -row["y"]) for row in rows]
    assert data.floats("opacities").tolist() == pytest.approx(
        [0.5, 1.0 / (1.0 + math.exp(-2.0)), 0.0]
    )
    red, green, blue, alpha = triples(data.floats("colors"), 4)[0]
    assert (red, green, blue) == pytest.approx((0.5 + splats.SH_C0, 0.5 - splats.SH_C0, 0.5))
    assert alpha == pytest.approx(0.5)
    # The median of the three log scales, as a linear radius.
    assert data.floats("radii").tolist() == pytest.approx([0.2, 1.2, 2.2], rel=1e-6)


def test_colours_clamp_and_large_log_scales_stay_finite():
    row = splat_row(0)
    row.update(f_dc_0=100.0, f_dc_1=-100.0, scale_0=500.0, scale_1=600.0, scale_2=700.0)
    data = decode(ply_bytes([row]))
    assert triples(data.floats("colors"), 4)[0][:2] == (1.0, 0.0)
    assert math.isfinite(data.floats("radii")[0])


def test_rows_are_thinned_by_stride_with_density_compensation():
    rows = [splat_row(i) for i in range(10)]
    data = decode(ply_bytes(rows), SplatOptions(4, "OPENGL"))
    assert (data.count, data.kept, data.step) == (10, 4, 3)
    # OPENGL saved (x, y, z) becomes Blender (x, -z, y).
    assert [row[1] for row in triples(data.floats("positions"))] == [2.0 * i for i in (0, 3, 6, 9)]
    assert data.floats("radii")[0] == pytest.approx(0.2 * math.sqrt(3), rel=1e-6)


def test_later_elements_are_not_read():
    data = (
        ply_bytes([splat_row(0)], elements=[("camera", 1, ["property float fov"])])
        + b"\x00\x00\x80\x3f"
    )
    assert decode(data).kept == 1


@pytest.mark.parametrize("known_size", [True, False])
def test_truncated_rows_are_rejected(known_size):
    data = ply_bytes([splat_row(i) for i in range(4)])[:-1]
    parsed, reader = header(data)
    size = len(data) if known_size else None
    with pytest.raises(SplatError, match="truncated"):
        splat_ply.decode(reader, parsed, options=SplatOptions(10, "OPENCV"), size=size)


@pytest.mark.parametrize("name", ["x", "f_dc_1", "opacity", "scale_2"])
@pytest.mark.parametrize("value", [math.inf, math.nan])
def test_non_finite_columns_are_rejected(name, value):
    row = splat_row(0)
    row[name] = value
    with pytest.raises(SplatError, match="non-finite"):
        decode(ply_bytes([splat_row(1), row]))


def test_vertex_count_is_bounded_before_rows_are_read():
    data = ply_bytes([splat_row(0)]).replace(b"element vertex 1", b"element vertex 20000001")
    with pytest.raises(SplatError, match="20,000,000"):
        decode(data)
