# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded splat snapshots: options, thinning, .splat records and fail-closed parsing."""

import gzip
import io
import math
import random
import struct
import threading

import pytest
from splat_files import ply_bytes, splat_record, splat_row, spz_payload

from scenario.core.scene import splats, spz
from scenario.core.scene.splats import SplatError, SplatOptions

OPENGL = SplatOptions(1000, "OPENGL")
OPENCV = SplatOptions(1000, "OPENCV")


def records(count):
    return b"".join(
        splat_record(
            (i, 2.0 * i, -3.0 * i),
            (0.1, 0.2 + i, 0.05),
            (255, 0, 51, 102),
        )
        for i in range(count)
    )


def decode_splat(data, options=OPENGL, **kwargs):
    return splats.decode_splat(io.BytesIO(data), options=options, size=len(data), **kwargs)


def rows(data, name, width):
    values = data.floats(name).tolist()
    return [tuple(values[i : i + width]) for i in range(0, len(values), width)]


@pytest.mark.parametrize(
    "max_points, axes",
    [(0, "OPENGL"), (2_000_001, "OPENGL"), (True, "OPENGL"), (1.0, "OPENGL"), (1, "Y_UP"), (1, [])],
)
def test_options_are_bounded_and_explicit(max_points, axes):
    with pytest.raises(ValueError):
        SplatOptions(max_points, axes)


def test_reviewed_choices_fit_the_decoder_bound():
    assert splats.DEFAULT_MAX_POINTS in splats.MAX_POINTS_CHOICES
    assert max(splats.MAX_POINTS_CHOICES) == splats.MAX_KEPT_POINTS
    assert set(splats.FORMAT_AXES.values()) == splats.AXES


@pytest.mark.parametrize(
    "count, max_points, plan",
    [(1, 5, (1, 1)), (100, 25, (4, 25)), (101, 25, (5, 21)), (10, 10, (1, 10)), (11, 10, (2, 6))],
)
def test_stride_plan_never_exceeds_the_kept_bound(count, max_points, plan):
    assert splats.plan(count, max_points) == plan
    assert plan[1] <= max_points


@pytest.mark.parametrize("count", [0, splats.MAX_SOURCE_POINTS + 1, True])
def test_empty_or_oversized_point_counts_are_rejected(count):
    with pytest.raises(SplatError):
        splats.plan(count, 10)


@pytest.mark.parametrize("chunk", [1 << 22, 64, 7])
@pytest.mark.parametrize(
    "size, count, step, fields",
    [
        (1, 50, 3, [(0, 1)]),
        (3, 50, 1, [(0, 1), (1, 1), (2, 1)]),
        (9, 40, 7, [(0, 3), (3, 3), (6, 3)]),
        (32, 9, 4, [(28, 4), (0, 12), (24, 1)]),
        (40, 13, 2, [(36, 4), (4, 4)]),
    ],
)
def test_kept_fields_match_simple_slicing_across_chunk_layouts(
    monkeypatch, chunk, size, count, step, fields
):
    monkeypatch.setattr(splats, "CHUNK_BYTES", chunk)
    data = bytes(random.Random(size * count).randbytes(size * count)) + b"tail"
    reader = splats.Reader(io.BytesIO(data))
    kept = splats.kept_fields(reader, count, size, step, fields)
    rows = [data[i * size : (i + 1) * size] for i in range(0, count, step)]
    assert kept == tuple(
        b"".join(row[offset : offset + width] for row in rows) for offset, width in fields
    )
    assert reader.read(4) == b"tail"


def test_splat_records_decode_to_blender_axes_colours_and_radii():
    data = decode_splat(records(3))
    assert (data.format, data.version, data.count, data.kept, data.step) == ("splat", None, 3, 3, 1)
    # OPENGL saved (x, y, z) becomes Blender (x, -z, y).
    assert rows(data, "positions", 3) == [(0.0, 0.0, 0.0), (1.0, 3.0, 2.0), (2.0, 6.0, 4.0)]
    assert data.bounds == ((0.0, 0.0, 0.0), (2.0, 6.0, 4.0))
    red, green, blue, alpha = rows(data, "colors", 4)[1]
    assert (red, green) == (1.0, 0.0) and blue == pytest.approx(0.2)
    assert alpha == pytest.approx(0.4) == data.floats("opacities")[1]
    assert data.floats("radii").tolist() == pytest.approx([0.1, 0.1, 0.1])
    other = decode_splat(records(3), OPENCV)
    # OPENCV saved (x, y, z) becomes Blender (x, z, -y).
    assert rows(other, "positions", 3)[2] == (2.0, -6.0, -4.0)


def test_splat_thinning_is_deterministic_and_compensates_density():
    data = decode_splat(records(10), SplatOptions(4, "OPENGL"))
    assert (data.count, data.kept, data.step) == (10, 4, 3)
    assert [row[0] for row in rows(data, "positions", 3)] == [0.0, 3.0, 6.0, 9.0]
    assert data.floats("radii")[0] == pytest.approx(0.1 * math.sqrt(3))


@pytest.mark.parametrize("size", [0, 31, 33])
def test_splat_files_must_be_whole_records(size):
    with pytest.raises(SplatError, match="32-byte"):
        splats.decode_splat(io.BytesIO(bytes(size)), options=OPENGL, size=size)


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
@pytest.mark.parametrize("field", ["position", "scale"])
def test_non_finite_splat_values_are_rejected(field, value):
    position, scale = [(0.0, 0.0, 0.0)], [(0.1, 0.1, 0.1)]
    (position if field == "position" else scale)[0] = (1.0, value, 1.0)
    data = splat_record(position[0], scale[0], (1, 2, 3, 4)) + records(1)
    with pytest.raises(SplatError, match="non-finite"):
        decode_splat(data)


def test_truncated_stream_fails_without_partial_snapshot():
    data = records(4)
    with pytest.raises(SplatError, match="truncated"):
        splats.decode_splat(io.BytesIO(data[:-32]), options=OPENGL, size=len(data))


def test_snapshot_views_are_read_only_native_floats():
    data = decode_splat(records(2))
    view = data.floats("colors")
    assert view.readonly and view.format == "f" and len(view) == 8
    with pytest.raises(ValueError):
        data.floats("rotations")
    with pytest.raises(TypeError):
        view[0] = 1.0


@pytest.mark.parametrize(
    "change",
    [
        {"kept": 1},
        {"step": 0},
        {"positions": b""},
        {"colors": bytearray(32)},
        {"format": "ksplat"},
        {"bounds": ((0.0, 0.0, 0.0), (math.nan, 0.0, 0.0))},
        {"bounds": ((1.0, 0.0, 0.0), (0.0, 0.0, 0.0))},
        {"bounds": ((0.0, 0.0), (0.0, 0.0))},
    ],
)
def test_snapshot_rejects_inconsistent_arrays_and_bounds(change):
    data = decode_splat(records(2))
    values = {
        name: getattr(data, name)
        for name in (
            "format",
            "version",
            "axes",
            "count",
            "kept",
            "step",
            "positions",
            "colors",
            "opacities",
            "radii",
            "bounds",
        )
    }
    with pytest.raises(ValueError):
        splats.SplatData(**{**values, **change})


def test_dispatcher_selects_by_declared_media_type_only():
    data = records(2)
    assert splats.decode(io.BytesIO(data), "model/splat", options=OPENGL, size=64).kept == 2
    payload = spz_payload(3)
    result = splats.decode(io.BytesIO(payload), "model/spz", options=OPENGL, size=len(payload))
    assert result.format == "spz"
    for media_type in ("model/ksplat", "model/sog", "model/gltf-binary", "image/png"):
        with pytest.raises(SplatError, match="SPZ, PLY or .splat"):
            splats.decode(io.BytesIO(data), media_type, options=OPENGL, size=64)
    # A declared PLY is never sniffed into another format.
    with pytest.raises(SplatError):
        splats.decode(io.BytesIO(payload), "model/ply", options=OPENGL, size=len(payload))
    with pytest.raises(TypeError):
        splats.decode(io.BytesIO(data), "model/splat", options={"max_points": 2}, size=64)


def test_dispatcher_returns_no_snapshot_for_a_mesh_ply():
    data = ply_bytes([{"x": 1.0, "y": 2.0, "z": 3.0}], properties=[("x", "float")])
    assert (
        splats.decode(io.BytesIO(data), "application/x-ply", options=OPENGL, size=len(data)) is None
    )


@pytest.mark.parametrize("media_type", ["model/spz", "model/ply", "model/splat"])
def test_cancellation_stops_every_decoder(media_type):
    cancel = threading.Event()
    cancel.set()
    data = {
        "model/spz": spz_payload(5),
        "model/ply": ply_bytes([splat_row(0)]),
        "model/splat": records(1),
    }[media_type]
    with pytest.raises(splats.SplatCancelled):
        splats.decode(io.BytesIO(data), media_type, options=OPENGL, size=len(data), cancel=cancel)


def test_unexpected_parser_failures_fail_closed(monkeypatch):
    def broken(*args, **kwargs):
        raise IndexError("synthetic parser bug")

    monkeypatch.setattr(splats, "decode_splat", broken)
    with pytest.raises(SplatError, match="invalid"):
        splats.decode(io.BytesIO(b""), "model/splat", options=OPENGL, size=32)


def _mutations(data, rng, rounds):
    yield b""
    for cut in sorted({rng.randrange(len(data)) for _ in range(rounds)}):
        yield data[:cut]
    for _ in range(rounds):
        damaged = bytearray(data)
        for _ in range(rng.randint(1, 8)):
            damaged[rng.randrange(min(len(damaged), 96))] = rng.randrange(256)
        yield bytes(damaged)
        damaged = bytearray(data)
        damaged[rng.randrange(len(damaged))] ^= 1 << rng.randrange(8)
        yield bytes(damaged)


def _check(media_type, sample, options):
    try:
        result = splats.decode(io.BytesIO(sample), media_type, options=options, size=len(sample))
    except SplatError:
        return
    if result is None:
        assert media_type == "model/ply"
        return
    assert 1 <= result.kept <= options.max_points
    assert all(math.isfinite(value) for value in result.floats("positions"))
    assert all(0.0 <= value <= 1.0 for value in result.floats("colors"))


def _uncompressed_spz(count):
    header = struct.pack("<IIIBBBB", spz.MAGIC, 3, count, 1, 12, 0, 0)
    return header, bytes(random.Random(count).randbytes(count * (16 + 4 + 9)))


@pytest.mark.parametrize("seed", range(4))
def test_mutated_synthetic_files_fail_closed_or_decode_bounded_snapshots(seed):
    rng = random.Random(seed)
    options = SplatOptions(rng.choice([1, 3, 50]), rng.choice(sorted(splats.AXES)))
    samples = {
        "model/spz": spz_payload(40, version=rng.choice([2, 3]), sh_degree=1, seed=seed),
        "model/ply": ply_bytes([splat_row(i) for i in range(20)]),
        "model/splat": records(20),
    }
    for media_type, data in samples.items():
        for sample in _mutations(data, rng, 30):
            _check(media_type, sample, options)
    # Corrupt fields inside the inflated SPZ header, not only the compressed bytes.
    header, body = _uncompressed_spz(20)
    for _ in range(40):
        damaged = bytearray(header)
        damaged[rng.randrange(len(damaged))] = rng.randrange(256)
        _check("model/spz", gzip.compress(bytes(damaged) + body), options)
