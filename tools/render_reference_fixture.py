# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the first-party reference image fixture, or check a fresh render against it.

Blender runs this script through the isolated command wrapper, which owns a fresh
offline profile for the child and removes it afterwards:

    uv run --locked --no-env-file python tools/blender_env.py run --blender BLENDER -- \
      --background --factory-startup --python-exit-code 1 \
      --python tools/render_reference_fixture.py -- write PATH

`check PATH` renders the same scene again and compares its pixels with PATH
instead of writing. The scene is built from code with a fixed seed; no external
asset, add-on or network access is used. The PNG helpers import without Blender
so offline unit tests can verify the committed file.
"""

import argparse
import hashlib
import math
import os
import random
import struct
import sys
import tempfile
import zlib
from pathlib import Path

BLENDER_VERSION = (5, 1, 2)
SIZE = 512
SEED = 40
SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 8 * 1024 * 1024
MAX_SIDE = 4096


def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def encode_png(width, height, pixels):
    """Canonical 8-bit RGB PNG: IHDR, one IDAT and IEND, with filter 0 on every row."""
    stride = width * 3
    if not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE) or len(pixels) != stride * height:
        raise ValueError("Pixel data does not match the image size")
    raw = b"".join(b"\0" + pixels[row * stride : (row + 1) * stride] for row in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def read_chunks(data):
    """Return every chunk after checking the signature, lengths, CRCs and IEND."""
    if len(data) > MAX_BYTES or data[:8] != SIGNATURE:
        raise ValueError("Not a bounded PNG file")
    chunks, offset = [], 8
    while True:
        if offset + 12 > len(data):
            raise ValueError("Truncated PNG chunk")
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind, end = data[offset + 4 : offset + 8], offset + 12 + length
        if end > len(data):
            raise ValueError("Truncated PNG chunk")
        body = data[offset + 8 : end - 4]
        if zlib.crc32(kind + body) != struct.unpack(">I", data[end - 4 : end])[0]:
            raise ValueError("PNG chunk CRC mismatch")
        chunks.append((kind, body))
        offset = end
        if kind == b"IEND":
            break
    if offset != len(data) or chunks[0][0] != b"IHDR":
        raise ValueError("PNG must start with IHDR and end at IEND")
    return chunks


def _paeth(left, up, corner):
    estimate = left + up - corner
    a, b, c = abs(estimate - left), abs(estimate - up), abs(estimate - corner)
    if a <= b and a <= c:
        return left
    return up if b <= c else corner


def decode_png(data):
    """Decode a non-interlaced 8-bit RGB PNG into (width, height, rows, filters).

    Rows are top-down RGB bytes. Ancillary chunks are ignored; other formats fail.
    """
    chunks = read_chunks(data)
    width, height, depth, colour, method, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1]
    )
    if (depth, colour, method, filtering, interlace) != (8, 2, 0, 0, 0) or not (
        1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE
    ):
        raise ValueError("Expected a non-interlaced 8-bit RGB PNG")
    stride = width * 3
    expected = (stride + 1) * height
    decompressor = zlib.decompressobj()
    # Inflate at most one byte past the declared size: a small stream that would
    # expand far beyond its header then fails without being inflated in full.
    raw = decompressor.decompress(
        b"".join(body for kind, body in chunks if kind == b"IDAT"), expected + 1
    )
    if len(raw) != expected or not decompressor.eof:
        raise ValueError("PNG image data does not match its header")
    rows, previous, filters = bytearray(), bytearray(stride), set()
    for row in range(height):
        start = row * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1 : start + 1 + stride])
        if kind == 1:
            for i in range(3, stride):
                line[i] = (line[i] + line[i - 3]) & 255
        elif kind == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 255
        elif kind == 3:
            for i in range(stride):
                left = line[i - 3] if i >= 3 else 0
                line[i] = (line[i] + (left + previous[i]) // 2) & 255
        elif kind == 4:
            for i in range(stride):
                left = line[i - 3] if i >= 3 else 0
                corner = previous[i - 3] if i >= 3 else 0
                line[i] = (line[i] + _paeth(left, previous[i], corner)) & 255
        elif kind != 0:
            raise ValueError("Unknown PNG row filter")
        filters.add(kind)
        rows += line
        previous = line
    return width, height, bytes(rows), filters


def read_png(path):
    """Decode the PNG file at path, reading at most one byte past MAX_BYTES.

    A larger file then fails the size check without being read in full.
    """
    with Path(path).open("rb") as stream:
        return decode_png(stream.read(MAX_BYTES + 1))


def compare(expected, actual):
    """Return (differing pixel count, largest channel difference) for equal-size RGB data."""
    if len(expected) != len(actual) or len(expected) % 3:
        raise ValueError("Compare RGB images of the same size")
    if expected == actual:
        return 0, 0
    differing = largest = 0
    for i in range(0, len(expected), 3):
        delta = max(abs(expected[i + k] - actual[i + k]) for k in range(3))
        if delta:
            differing += 1
            largest = max(largest, delta)
    return differing, largest


def _mesh_object(bpy, bmesh, scene, name, build, colour, *, location, scale=(1, 1, 1)):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    try:
        build(bm)
        for face in bm.faces:
            # Smooth curved sides; keep flat caps, which are n-gons.
            face.smooth = len(face.verts) <= 4
        bm.to_mesh(mesh)
    finally:
        bm.free()
    item = bpy.data.objects.new(name, mesh)
    item.location, item.scale, item.color = location, scale, (*colour, 1.0)
    scene.collection.objects.link(item)
    return item


def build_scene(bpy, bmesh, mathutils):
    """A toadstool on a mossy base, with seeded spots and pebbles, in a fixed camera."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    rng = random.Random(SEED)

    def cone(radius1, radius2, depth):
        return lambda bm: bmesh.ops.create_cone(
            bm, cap_ends=True, segments=64, radius1=radius1, radius2=radius2, depth=depth
        )

    def sphere(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)

    def dome(bm):
        sphere(bm)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-6], context="VERTS")
        bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)

    def pebble(bm):
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)

    _mesh_object(
        bpy, bmesh, scene, "Base", cone(1.15, 1.05, 0.2), (0.25, 0.48, 0.2), location=(0, 0, 0.1)
    )
    _mesh_object(
        bpy, bmesh, scene, "Stem", cone(0.36, 0.27, 1.1), (0.93, 0.87, 0.74), location=(0, 0, 0.75)
    )
    cap_location, cap_scale = (0.0, 0.0, 1.22), (1.0, 1.0, 0.62)
    _mesh_object(
        bpy,
        bmesh,
        scene,
        "Cap",
        dome,
        (0.78, 0.1, 0.07),
        location=cap_location,
        scale=cap_scale,
    )
    spots = []
    while len(spots) < 9:
        azimuth, polar = rng.uniform(0, 2 * math.pi), rng.uniform(0.15, 1.2)
        point = mathutils.Vector(
            (
                math.sin(polar) * math.cos(azimuth),
                math.sin(polar) * math.sin(azimuth),
                math.cos(polar),
            )
        )
        if all((point - other).length > 0.42 for other in spots):
            spots.append(point)
    for index, point in enumerate(spots):
        radius = rng.uniform(0.08, 0.13)
        location = tuple(c + s * p for c, s, p in zip(cap_location, cap_scale, point, strict=True))
        _mesh_object(
            bpy,
            bmesh,
            scene,
            f"Spot{index}",
            sphere,
            (1.0, 0.98, 0.93),
            location=location,
            scale=(radius, radius, radius * 0.45),
        ).rotation_euler = point.to_track_quat("Z", "Y").to_euler()
    for index in range(5):
        azimuth, distance = rng.uniform(0, 2 * math.pi), rng.uniform(0.55, 0.9)
        size = rng.uniform(0.06, 0.11)
        shade = rng.uniform(0.45, 0.62)
        _mesh_object(
            bpy,
            bmesh,
            scene,
            f"Pebble{index}",
            pebble,
            (shade, shade, shade * 0.95),
            location=(distance * math.cos(azimuth), distance * math.sin(azimuth), 0.2 + size * 0.3),
            scale=(size, size * rng.uniform(0.7, 1.0), size * 0.6),
        )

    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.lens, camera.data.sensor_width = 50.0, 36.0
    camera.location = (0.0, -4.6, 2.35)
    target = mathutils.Vector((0.0, 0.0, 0.8))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Backdrop")
    scene.world.color = (0.62, 0.7, 0.78)
    return scene


def configure(scene):
    render = scene.render
    render.engine = "BLENDER_WORKBENCH"
    render.resolution_x = render.resolution_y = SIZE
    render.resolution_percentage = 100
    render.pixel_aspect_x = render.pixel_aspect_y = 1.0
    render.film_transparent = False
    render.dither_intensity = 0.0
    render.use_compositing = render.use_sequencer = False
    render.use_border = render.use_stamp = render.use_multiview = False
    render.use_file_extension = False
    settings = render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "IMAGE"
    settings.file_format = "PNG"
    settings.color_mode, settings.color_depth, settings.compression = "RGB", "8", 0
    scene.display_settings.display_device = "sRGB"
    view = scene.view_settings
    view.view_transform, view.look = "Standard", "None"
    view.exposure, view.gamma, view.use_curve_mapping = 0.0, 1.0, False
    scene.display.render_aa = "8"
    shading = scene.display.shading
    shading.light, shading.color_type = "STUDIO", "OBJECT"
    shading.show_shadows = shading.show_cavity = shading.show_object_outline = False
    shading.show_specular_highlight, shading.show_xray, shading.use_dof = True, False, False


def render(bpy, bmesh, mathutils, directory):
    scene = build_scene(bpy, bmesh, mathutils)
    configure(scene)
    output = directory / "render.png"
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    width, height, pixels, _ = read_png(output)
    if (width, height) != (SIZE, SIZE):
        raise RuntimeError("Blender rendered an unexpected image size")
    return pixels


def write(path, data):
    if path.is_symlink() or path.is_dir():
        raise ValueError("Write the fixture to a regular file path")
    handle, temporary = tempfile.mkstemp(prefix=".reference-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def tolerance(value):
    if not value.isdigit() or int(value) > 255:
        raise argparse.ArgumentTypeError("use a channel difference from 0 to 255")
    return int(value)


def main(argv):
    import bmesh
    import bpy
    import gpu
    import mathutils

    parser = argparse.ArgumentParser(prog="render_reference_fixture.py", description=__doc__)
    parser.add_argument("mode", choices=("write", "check"))
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--tolerance",
        type=tolerance,
        default=0,
        metavar="0-255",
        help="Largest accepted channel difference in check mode (default: exact)",
    )
    args = parser.parse_args(argv)
    if tuple(bpy.app.version) != BLENDER_VERSION or not bpy.app.background:
        raise RuntimeError(
            "Render the fixture in background Blender "
            + ".".join(map(str, BLENDER_VERSION))
            + f", not {bpy.app.version_string}"
        )
    with tempfile.TemporaryDirectory(prefix="reference-render-") as directory:
        pixels = render(bpy, bmesh, mathutils, Path(directory))
    print(
        f"Blender {bpy.app.version_string}, GPU backend {gpu.platform.backend_type_get()}, "
        f"pixels sha256 {hashlib.sha256(pixels).hexdigest()}",
        flush=True,
    )
    if args.mode == "write":
        data = encode_png(SIZE, SIZE, pixels)
        write(args.path, data)
        print(f"Wrote {args.path} sha256 {hashlib.sha256(data).hexdigest()}", flush=True)
        return
    width, height, expected, _ = read_png(args.path)
    if (width, height) != (SIZE, SIZE):
        raise RuntimeError("The compared fixture has an unexpected size")
    differing, largest = compare(expected, pixels)
    print(f"{differing} differing pixels, largest channel difference {largest}", flush=True)
    if largest > args.tolerance:
        raise RuntimeError("The fresh render differs from the fixture beyond the tolerance")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
