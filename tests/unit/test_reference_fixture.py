# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The committed first-party reference render is a pinned, valid and documented PNG.

Rendering needs Blender 5.1.2 and is checked by tools/render_reference_fixture.py;
these offline tests verify the committed bytes and the helpers that read them.
"""

import argparse
import hashlib
import io
import json
import random
import re
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from scenario.core.jobs import upload_sources
from scenario.core.jobs.store import JobOrigin, JobScope
from tools import render_reference_fixture as fixture
from tools import smoke_inputs

ROOT = Path(__file__).resolve().parents[2]
RELATIVE = "tests/fixtures/synthetic/reference-toadstool-512.png"
REFERENCE = ROOT / RELATIVE
FILE_SHA256 = "b70e8debff0ba0fc7dd8823a9a38229600e3fd7b8f22a1a32c490b4310182e02"
PIXEL_SHA256 = "5ec27e71b80a93737e51e354eac42d1341d0737d90f0cede8f4a8dcd269e4a71"
BACKDROP = bytes((206, 218, 228))


def pixel(rows, width, x, y):
    start = (y * width + x) * 3
    return rows[start : start + 3]


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def paeth(left, up, corner):
    """The PNG specification's predictor, independent of the helper under test."""
    estimate = left + up - corner
    distances = [abs(estimate - left), abs(estimate - up), abs(estimate - corner)]
    return (left, up, corner)[distances.index(min(distances))]


def filtered_png(width, height, rows, kinds):
    """Encode RGB rows with an explicit PNG filter type per row (forward filters)."""
    stride, previous, raw = width * 3, bytes(width * 3), bytearray()
    for row, kind in zip(range(height), kinds, strict=True):
        line = rows[row * stride : (row + 1) * stride]
        out = bytearray()
        for i, value in enumerate(line):
            left = line[i - 3] if i >= 3 else 0
            corner = previous[i - 3] if i >= 3 else 0
            predictor = (
                0,
                left,
                previous[i],
                (left + previous[i]) // 2,
                paeth(left, previous[i], corner),
            )[kind]
            out.append((value - predictor) & 255)
        raw += bytes((kind,)) + out
        previous = line
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        fixture.SIGNATURE
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw)))
        + chunk(b"IEND", b"")
    )


def noise(width, height, seed=7):
    rng = random.Random(seed)
    return bytes(
        (x * 9 + y * 3 + rng.randrange(40)) & 255
        for y in range(height)
        for x in range(width)
        for _ in range(3)
    )


def test_committed_reference_is_the_pinned_canonical_render():
    data = REFERENCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == FILE_SHA256
    assert len(data) < 256 * 1024
    assert [kind for kind, _ in fixture.read_chunks(data)] == [b"IHDR", b"IDAT", b"IEND"]
    width, height, rows, filters = fixture.decode_png(data)
    assert (width, height, filters) == (fixture.SIZE, fixture.SIZE, {0})
    assert hashlib.sha256(rows).hexdigest() == PIXEL_SHA256


def test_pillow_reads_the_same_rgb_pixels_without_metadata():
    with Image.open(REFERENCE) as image:
        image.verify()
    with Image.open(REFERENCE) as image:
        assert (image.format, image.mode, image.size, image.info) == ("PNG", "RGB", (512, 512), {})
        assert image.tobytes() == fixture.decode_png(REFERENCE.read_bytes())[2]


def test_reference_frames_one_object_on_a_plain_backdrop():
    width, height, rows, _ = fixture.decode_png(REFERENCE.read_bytes())
    border = 48
    edge = [
        pixel(rows, width, x, y)
        for y in range(height)
        for x in range(width)
        if min(x, y, width - 1 - x, height - 1 - y) < border
    ]
    assert set(edge) == {BACKDROP}
    assert pixel(rows, width, width // 2, height // 2) != BACKDROP
    colours = [rows[i : i + 3] for i in range(0, len(rows), 3)]
    assert 0.2 < sum(colour != BACKDROP for colour in colours) / len(colours) < 0.5
    assert len(set(colours)) > 1000


@pytest.mark.parametrize(
    "kinds", [[0] * 12, [1] * 12, [2] * 12, [3] * 12, [4] * 12, [4, 3, 2, 1, 0] * 2 + [4, 4]]
)
def test_decoder_reverses_every_png_row_filter(kinds):
    rows = noise(16, 12)
    width, height, decoded, filters = fixture.decode_png(filtered_png(16, 12, rows, kinds))
    assert (width, height, decoded, filters) == (16, 12, rows, set(kinds))


def test_decoder_matches_pillow_adaptive_encoding():
    rows = noise(37, 23, seed=3)
    stream = io.BytesIO()
    Image.frombytes("RGB", (37, 23), rows).save(stream, format="PNG")
    assert fixture.decode_png(stream.getvalue())[:3] == (37, 23, rows)


def test_canonical_encoder_round_trips_through_pillow():
    rows = noise(11, 6, seed=5)
    data = fixture.encode_png(11, 6, rows)
    assert fixture.decode_png(data) == (11, 6, rows, {0})
    with Image.open(io.BytesIO(data)) as image:
        assert (image.mode, image.size, image.tobytes()) == ("RGB", (11, 6), rows)
    with pytest.raises(ValueError, match="does not match"):
        fixture.encode_png(11, 6, rows[:-1])


def replace_header(data, header):
    end = 8 + 8 + 13 + 4
    return data[:8] + chunk(b"IHDR", header) + data[end:]


RAW = b"\0" + bytes(6) + b"\0" + bytes(6)
IDAT = chunk(b"IDAT", zlib.compress(RAW, 9))


def unterminated(data):
    stream = zlib.compressobj(9)
    return stream.compress(data) + stream.flush(zlib.Z_SYNC_FLUSH)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: b"\x89PNG\r\n\x1a\x00" + data[8:], "Not a bounded PNG"),
        (lambda data: data[:-1], "Truncated"),
        (lambda data: data + b"\0", "end at IEND"),
        (lambda data: data[:29] + bytes((data[29] ^ 1,)) + data[30:], "CRC mismatch"),
        (lambda data: data[: -len(chunk(b"IEND", b""))], "Truncated"),
        (lambda data: chunk(b"tEXt", b"x") + data, "Not a bounded PNG"),
        (lambda data: data[:8] + chunk(b"tEXt", b"x") + data[8:], "start with IHDR"),
        (lambda data: replace_header(data, struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0)), "RGB"),
        (lambda data: replace_header(data, struct.pack(">IIBBBBB", 2, 2, 16, 2, 0, 0, 0)), "RGB"),
        (lambda data: replace_header(data, struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 1)), "RGB"),
        (lambda data: replace_header(data, struct.pack(">IIBBBBB", 0, 2, 8, 2, 0, 0, 0)), "RGB"),
        (lambda data: replace_header(data, struct.pack(">IIBBBBB", 2, 3, 8, 2, 0, 0, 0)), "header"),
        (lambda data: data.replace(IDAT, chunk(b"IDAT", zlib.compress(RAW[:-1]))), "header"),
        (lambda data: data.replace(IDAT, chunk(b"IDAT", zlib.compress(RAW + b"\0"))), "header"),
        (lambda data: data.replace(IDAT, chunk(b"IDAT", unterminated(RAW))), "header"),
        (lambda data: data.replace(IDAT, chunk(b"IDAT", zlib.compress(b"\5" + RAW[1:]))), "filter"),
    ],
)
def test_decoder_rejects_invalid_or_unsupported_png(mutate, message):
    data = fixture.encode_png(2, 2, bytes(12))
    assert IDAT in data
    assert fixture.decode_png(data)[:2] == (2, 2)
    with pytest.raises(ValueError, match=message):
        fixture.decode_png(mutate(data))


def test_compare_counts_differing_pixels_and_largest_channel_change():
    rows = noise(4, 4)
    changed = bytearray(rows)
    changed[0] ^= 1  # red of pixel 0
    changed[10] = (changed[10] + 7) & 255  # green of pixel 3
    changed[20] ^= 2  # blue of pixel 6
    assert fixture.compare(rows, rows) == (0, 0)
    assert fixture.compare(rows, bytes(changed)) == (3, 7)
    with pytest.raises(ValueError):
        fixture.compare(rows, rows[:-3])


@pytest.mark.parametrize("value", ["0", "2", "255"])
def test_tolerance_accepts_channel_differences(value):
    assert fixture.tolerance(value) == int(value)


@pytest.mark.parametrize("value", ["", "-1", "256", "1.5", "x"])
def test_tolerance_rejects_other_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        fixture.tolerance(value)


def test_fixture_readme_records_the_command_version_and_digests():
    text = (ROOT / "tests/fixtures/README.md").read_text(encoding="utf-8")
    for expected in (
        RELATIVE,
        "tools/render_reference_fixture.py -- write",
        "tools/render_reference_fixture.py -- check",
        "Blender 5.1.2",
        FILE_SHA256,
        PIXEL_SHA256,
    ):
        assert expected in text


def documented_plan():
    text = (ROOT / "tests/smoke/README.md").read_text(encoding="utf-8")
    plans = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", text, re.S)]
    matches = [
        plan
        for plan in plans
        if plan.get("schema_version") == 2
        and any(item.get("file") == RELATIVE for item in plan["inputs"])
    ]
    assert len(matches) == 1
    return matches[0]


def test_smoke_readme_reference_plan_names_the_committed_bytes():
    plan = documented_plan()
    entries = smoke_inputs.validate(plan, SimpleNamespace(project_id=None))
    assert [(item["kind"], item["content_type"], item["sha256"]) for item in entries] == [
        ("image", "image/png", FILE_SHA256)
    ]
    root = ROOT.resolve()
    assert smoke_inputs.source_paths(entries, root) == {entries[0]["name"]: root / RELATIVE}


def test_shared_upload_staging_accepts_the_documented_digest(tmp_path):
    staged = tmp_path / "staged"
    staged.mkdir()
    entry = documented_plan()["inputs"][0]
    intent = upload_sources.UploadSources(staged).stage(
        REFERENCE,
        request_id="reference",
        scope=JobScope("https://service.example.invalid/v1", "account"),
        origin=JobOrigin("file", "fixture", "revision"),
        kind=entry["kind"],
        content_type=entry["content_type"],
        expected_sha256=entry["sha256"],
    )
    assert (intent.file_sha256, intent.file_size) == (FILE_SHA256, REFERENCE.stat().st_size)
