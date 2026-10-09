# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import gzip
import io
import math
import struct
import threading
import time

import pytest
from splat_files import spz_payload

from scenario.core.scene import splats, spz
from scenario.core.scene.splats import SplatError, SplatOptions

POSITIONS = [(0.0, 0.0, 0.0), (1.5, -2.25, 3.0), (-100.125, 50.5, 0.75)]
COLORS = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.2, 0.4, 0.6)]
OPENGL = SplatOptions(1000, "OPENGL")


def test_roundtrip_positions_colors_alphas_scales(tmp_path):
    path = tmp_path / "cloud.spz"
    positions = [(0.0, 0.0, 0.0), (1.5, -2.25, 3.0), (-100.125, 50.5, 0.75)]
    colors = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.2, 0.4, 0.6)]
    spz.write_spz(path, positions, colors, alphas=[1.0, 0.5, 0.0], scales=[0.01, 0.1, 1.0])
    data = spz.read_spz(path)
    assert data["count"] == 3 and data["kept"] == 3 and data["step"] == 1 and data["version"] == 2
    for got, want in zip(data["positions"], positions, strict=True):
        assert all(abs(a - b) < 1e-3 for a, b in zip(got, want, strict=True))
    for got, want in zip(data["colors"], colors, strict=True):
        assert all(abs(a - b) < 0.02 for a, b in zip(got, want, strict=True))
    assert [round(a, 2) for a in data["alphas"]] == [1.0, 0.5, 0.0]
    assert all(abs(a - b) / b < 0.1 for a, b in zip(data["scales"], [0.01, 0.1, 1.0], strict=True))


def test_subsampling_keeps_every_nth_point(tmp_path):
    path = tmp_path / "many.spz"
    positions = [(float(i), 0.0, 0.0) for i in range(100)]
    spz.write_spz(path, positions, [(0.5, 0.5, 0.5)] * 100)
    data = spz.read_spz(path, max_points=25)
    assert data["count"] == 100 and data["kept"] == 25 and data["step"] == 4
    assert data["positions"][1][0] == pytest.approx(4.0, abs=1e-3)


def test_axis_conversion_and_bad_files(tmp_path):
    assert spz.y_up_to_z_up((1.0, 2.0, 3.0)) == (1.0, -3.0, 2.0)
    bad = tmp_path / "bad.spz"
    with gzip.open(bad, "wb") as handle:
        handle.write(b"not a splat file at all")
    with pytest.raises(spz.SpzError):
        spz.read_spz(bad)


def test_sniff_recognises_a_splat_saved_as_bin(tmp_path):
    path = tmp_path / "world.bin"
    spz.write_spz(path, [(0.0, 0.0, 0.0)], [(0.5, 0.5, 0.5)])
    assert spz.sniff_spz(path)
    (tmp_path / "plain.bin").write_bytes(b"\x00\x01\x02\x03")
    assert not spz.sniff_spz(tmp_path / "plain.bin")
    from scenario.core.scene import placement

    assert placement.importer_for(path) == "spz"
    assert placement.importer_for(tmp_path / "plain.bin") is None


def encoded(tmp_path, *, version=2, sh_degree=0, positions=POSITIONS, colors=COLORS, **kwargs):
    path = tmp_path / f"cloud-v{version}-sh{sh_degree}.spz"
    spz.write_spz(path, positions, colors, version=version, sh_degree=sh_degree, **kwargs)
    return path.read_bytes()


def decode(data, options=OPENGL, **kwargs):
    return spz.decode_spz(io.BytesIO(data), options=options, size=len(data), **kwargs)


def triples(values, width=3):
    values = values.tolist()
    return [tuple(values[i : i + width]) for i in range(0, len(values), width)]


@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.parametrize("sh_degree", [0, 3])
def test_v2_and_v3_decode_to_blender_axes_without_reading_rotations_or_sh(
    tmp_path, version, sh_degree
):
    data = encoded(tmp_path, version=version, sh_degree=sh_degree, alphas=[1.0, 0.5, 0.0])
    result = decode(data)
    assert (result.format, result.version, result.count, result.kept) == ("spz", version, 3, 3)
    # OPENGL saved (x, y, z) becomes Blender (x, -z, y), exactly for 12 fractional bits.
    assert triples(result.floats("positions")) == [(x, -z, y) for x, y, z in POSITIONS]
    assert result.bounds == ((-100.125, -3.0, -2.25), (1.5, 0.0, 50.5))
    assert result.floats("opacities").tolist() == pytest.approx([1.0, 128 / 255, 0.0])
    colors = triples(result.floats("colors"), 4)
    for got, want in zip(colors, COLORS, strict=True):
        assert got[:3] == pytest.approx(want, abs=0.02)
    assert [color[3] for color in colors] == result.floats("opacities").tolist()
    assert result.floats("radii").tolist() == pytest.approx([0.01] * 3, rel=0.1)


def test_opencv_axes_and_density_compensation(tmp_path):
    positions = [(float(i), 2.0 * i, -1.0) for i in range(10)]
    data = encoded(tmp_path, positions=positions, colors=[(0.5, 0.5, 0.5)] * 10, scales=[0.5] * 10)
    result = decode(data, SplatOptions(3, "OPENCV"))
    assert (result.count, result.kept, result.step) == (10, 3, 4)
    # OPENCV saved (x, y, z) becomes Blender (x, z, -y).
    assert triples(result.floats("positions")) == [
        (0.0, -1.0, -0.0),
        (4.0, -1.0, -8.0),
        (8.0, -1.0, -16.0),
    ]
    assert result.floats("radii").tolist() == pytest.approx([0.5 * math.sqrt(4)] * 3, rel=0.05)


def test_version_one_is_rejected_instead_of_misread_as_fixed_point():
    header = struct.pack("<IIIBBBB", spz.MAGIC, 1, 1, 0, 0, 0, 0)
    with pytest.raises(spz.SpzError, match="v1"):
        decode(gzip.compress(header + bytes(6 + 1 + 3 + 3 + 3)))


def test_plaintext_version_four_is_rejected_with_a_retained_file_message():
    header = b"NGSP" + struct.pack("<IIBBBBI12x", 4, 1, 0, 12, 0, 4, 32)
    with pytest.raises(spz.SpzError, match=r"v4 \(ZSTD\).*saved file is kept"):
        decode(header + bytes(64))


@pytest.mark.parametrize("version", [0, 4, 5, 2**32 - 1])
def test_other_gzip_versions_are_unsupported(version):
    header = struct.pack("<IIIBBBB", spz.MAGIC, version, 1, 0, 12, 0, 0)
    with pytest.raises(spz.SpzError, match="version"):
        decode(gzip.compress(header + bytes(32)))


@pytest.mark.parametrize(
    "fields, message",
    [
        ((2, 0, 0, 12), "point count"),
        ((2, splats.MAX_SOURCE_POINTS + 1, 0, 12), "point count"),
        ((2, 5, 5, 12), "layout"),
        ((2, 5, 0, 24), "layout"),
    ],
)
def test_header_bounds_are_checked_before_reading_points(fields, message):
    version, count, sh_degree, bits = fields
    header = struct.pack("<IIIBBBB", spz.MAGIC, version, count, sh_degree, bits, 0, 0)
    with pytest.raises(SplatError, match=message):
        spz.decode_spz(io.BytesIO(gzip.compress(header)), options=SplatOptions(10, "OPENGL"))


def test_point_count_must_fit_the_reference_compression_bound():
    header = struct.pack("<IIIBBBB", spz.MAGIC, 2, 1_000_000, 0, 12, 0, 0)
    data = gzip.compress(header)
    with pytest.raises(spz.SpzError, match="compressed size"):
        decode(data)


@pytest.mark.parametrize("keep", [0, 16 + 9, 16 + 30, 16 + 44])
def test_truncation_inside_decoded_blocks_is_rejected(tmp_path, keep):
    raw = gzip.decompress(encoded(tmp_path, version=3))
    with pytest.raises(SplatError, match="truncated"):
        decode(gzip.compress(raw[:keep]))


def test_truncation_after_scales_is_not_read(tmp_path):
    raw = gzip.decompress(encoded(tmp_path, version=3, sh_degree=2))
    assert decode(gzip.compress(raw[: 16 + 3 * 16])).kept == 3


@pytest.mark.parametrize("data", [b"", b"\x1f", b"\x1f\x8b\x08\x00garbage", b"PK\x03\x04"])
def test_damaged_or_foreign_streams_are_rejected(data):
    with pytest.raises(SplatError):
        decode(data)


def test_cancellation_between_chunks(monkeypatch):
    cancel = threading.Event()
    monkeypatch.setattr(splats, "CHUNK_BYTES", 64)
    original = splats.GzipReader._chunk

    def chunk(self, size):
        cancel.set()
        return original(self, size)

    monkeypatch.setattr(splats.GzipReader, "_chunk", chunk)
    data = spz_payload(200)
    with pytest.raises(splats.SplatCancelled):
        decode(data, cancel=cancel)


def test_two_million_points_decode_in_bounded_time():
    """Timing smoke: record, do not treat the loose ceiling as performance acceptance."""
    data = spz_payload(2_000_000, version=3)
    start = time.perf_counter()
    result = decode(data, SplatOptions(1_000_000, "OPENGL"))
    elapsed = time.perf_counter() - start
    assert (result.count, result.kept, result.step) == (2_000_000, 1_000_000, 2)
    assert len(result.positions) == 12 * result.kept
    assert elapsed < 60
