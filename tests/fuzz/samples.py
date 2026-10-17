# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal valid inputs built in code, and the seed corpus of every harness.

Each seed starts with its harness mode byte. ``python samples.py OUT`` writes one
``<harness>_seed_corpus.zip`` per harness, as ClusterFuzzLite expects.
"""

import json
import struct
import sys
import zipfile
from pathlib import Path


def box(kind, *parts):
    payload = b"".join(parts)
    return struct.pack(">I4s", 8 + len(payload), kind) + payload


def full(kind, payload, version=0):
    return box(kind, bytes([version, 0, 0, 0]), payload)


def descriptor(tag, payload):
    return bytes([tag, len(payload)]) + payload


def avc1(width=64, height=64, profile=100):
    fields = bytes(6) + struct.pack(">H", 1) + bytes(16) + struct.pack(">HH", width, height)
    return box(b"avc1", fields, bytes(50), box(b"avcC", bytes([1, profile, 0, 31])))


def mp4a(rate=48000, channels=2):
    fields = bytes(6) + struct.pack(">H", 1)
    fields += struct.pack(">HH4sHHHHI", 0, 0, bytes(4), channels, 16, 0, 0, rate << 16)
    es = struct.pack(">HB", 1, 0) + descriptor(0x04, bytes([0x40]) + bytes(12))
    return box(b"mp4a", fields, full(b"esds", descriptor(0x03, es)))


def track(handler, entry, *, scale, timing, presented):
    count = sum(number for number, _ in timing)
    table = struct.pack(">I", len(timing)) + b"".join(struct.pack(">II", *row) for row in timing)
    return box(
        b"trak",
        full(b"tkhd", struct.pack(">IIIII", 0, 0, 1, 0, presented) + bytes(60)),
        box(
            b"mdia",
            full(b"mdhd", struct.pack(">IIII", 0, 0, scale, 0) + bytes(4)),
            full(b"hdlr", bytes(4) + handler + bytes(12) + b"\0"),
            box(
                b"minf",
                box(
                    b"stbl",
                    full(b"stsd", struct.pack(">I", 1) + entry),
                    full(b"stts", table),
                    full(b"stsz", struct.pack(">II", 0, count)),
                ),
            ),
        ),
    )


def mp4(tracks=None, scale=1000):
    """An H.264 video and AAC audio movie, or the given tracks, with an empty mdat."""
    if tracks is None:
        tracks = (
            track(b"vide", avc1(), scale=12288, timing=[(48, 512)], presented=2000),
            track(b"soun", mp4a(), scale=48000, timing=[(93, 1024)], presented=2000),
        )
    mvhd = full(b"mvhd", struct.pack(">IIII", 0, 0, scale, 2000) + bytes(80))
    head = box(b"ftyp", b"isom", bytes(4), b"isomavc1")
    return head + box(b"mdat", bytes(32)) + box(b"moov", mvhd, *tracks)


def largesize(data):
    """The same top-level boxes with 64-bit ``largesize`` headers (ISO/IEC 14496-12 4.2)."""
    out, offset = [], 0
    while offset + 8 <= len(data):
        size, kind = struct.unpack_from(">I4s", data, offset)
        header = 8
        if size == 1:
            size, header = struct.unpack_from(">Q", data, offset + 8)[0], 16
        elif size == 0:
            size = len(data) - offset
        if size < header or offset + size > len(data):
            return None
        body = data[offset + header : offset + size]
        out.append(struct.pack(">I4sQ", 1, kind, 16 + len(body)) + body)
        offset += size
    return b"".join(out) if offset == len(data) else None


STATIC_GLTF = {
    "asset": {"version": "2.0"},
    "scene": 0,
    "scenes": [{"nodes": [0]}],
    "nodes": [{"mesh": 0}],
    "buffers": [{"byteLength": 4}],
    "accessors": [{"count": 1}],
}
RIGGED_GLTF = {
    **STATIC_GLTF,
    "nodes": [{"mesh": 0}, {}],
    "skins": [{"joints": [0, 1]}],
    "animations": [{"channels": [{"target": {"node": 1, "path": "rotation"}}]}],
}


def glb(document, binary=b"\0\0\0\0"):
    text = document if isinstance(document, bytes) else json.dumps(document).encode()
    text += b" " * (-len(text) % 4)
    binary += b"\0" * (-len(binary) % 4)
    chunks = struct.pack("<I4s", len(text), b"JSON") + text
    chunks += struct.pack("<I4s", len(binary), b"BIN\0") + binary
    return struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks


MESH_PLY = (
    b"ply\nformat ascii 1.0\ncomment fuzz\nelement vertex 3\nproperty float x\n"
    b"property float y\nproperty float z\nelement face 1\n"
    b"property list uchar int vertex_indices\nend_header\n0 0 0\n1 0 0\n0 1 0\n3 0 1 2\n"
)
SPLAT_PROPERTIES = ("x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity")
SPLAT_PROPERTIES += ("scale_0", "scale_1", "scale_2")


def splat_ply(count=2):
    lines = ["ply", "format binary_little_endian 1.0", f"element vertex {count}"]
    lines += [f"property float {name}" for name in SPLAT_PROPERTIES]
    header = ("\n".join([*lines, "end_header"]) + "\n").encode("ascii")
    return header + bytes(count * 4 * len(SPLAT_PROPERTIES))


def decoder_output(rate=48000, channels=2, frames=960):
    """``envelope.json`` and ``blocks.bin`` as the waveform worker writes them."""
    block = max(1, rate // 100)
    header = {"format": 1, "sample_rate": rate, "channels": channels, "frames": frames}
    header["block"] = block
    blocks = []
    for index in range(-(-frames // block)):
        size = min(block, frames - index * block)
        peak = 0.5
        blocks.append(struct.pack("<dd", size * channels * peak * peak / 2, peak))
    return json.dumps(header).encode(), b"".join(blocks)


def audio_seed(header, blocks):
    return bytes([0]) + struct.pack(">H", len(header)) + header + blocks


def requests():
    call = {"name": "echo", "arguments": {"a": 1}}
    return [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": "x", "method": "tools/call", "params": call},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        [{"jsonrpc": "2.0", "id": 2, "method": "ping"}, {"jsonrpc": "2.0", "id": 3}],
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "deferred"}},
    ]


GUARDED = (b"localhost:8080", b"[::1]", b"http://127.0.0.1:9")


def seeds():
    """The seed inputs of each harness, by harness module name."""
    # Python's JSON decoder recurses per nesting level; 3.11 stops near 1000 levels.
    nested = b"[" * 5000 + b"]" * 5000
    # Varied bytes drive the data provider of structured modes through many choices.
    varied = bytes(range(7, 256, 3)) * 4
    return {
        "fuzz_mcp_protocol": [bytes([0]) + json.dumps(item).encode() for item in requests()]
        + [bytes([0]) + nested, bytes([1]) + varied, bytes([2]) + varied],
        "fuzz_mcp_guards": [bytes([0]) + value for value in GUARDED]
        + [bytes([mode]) + varied for mode in (1, 2, 3)],
        "fuzz_upload_policy": [bytes([0]) + varied, bytes([0]) + varied[::-1]],
        "fuzz_glb": [bytes([0]) + glb(STATIC_GLTF), bytes([1]) + glb(RIGGED_GLTF)]
        + [bytes([2]) + varied],
        "fuzz_mp4": [bytes([0]) + mp4(), bytes([1]) + mp4(), bytes([2]) + varied],
        "fuzz_model_formats": [bytes([0]) + MESH_PLY, bytes([1]) + splat_ply()]
        + [bytes([mode]) + varied for mode in (2, 3, 4)],
        "fuzz_audio": [
            audio_seed(*decoder_output()),
            audio_seed(*decoder_output(100, 1, 7)),
            audio_seed(nested[:2000] + nested[-2000:], b""),
        ]
        + [bytes([mode]) + varied for mode in (1, 2, 3)],
    }


def write_corpora(directory):
    for name, inputs in seeds().items():
        with zipfile.ZipFile(Path(directory) / f"{name}_seed_corpus.zip", "w") as archive:
            for index, data in enumerate(inputs):
                archive.writestr(f"seed-{index}", data)


if __name__ == "__main__":
    write_corpora(sys.argv[1])
