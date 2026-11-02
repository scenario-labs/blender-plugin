# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep the source's own texture on chosen faces of a retextured mesh.

`review` reads the captured sources (Edit Mode face selection, a rig's head
weights, scene positions) and resolves a `KeptRegion` with
`core.scene.kept_texture`. `composite` runs once the RETEXTURE application has
given the sources the result's UVs and materials: on each new result image, the
texels under kept faces take the source's own map, sampled through the source's
UVs and blended by the region's weights, and the empty texels around them take
their colour so filtering shows no seam. Maps are paired by their role in each
material's Principled BSDF: base colour, normal, roughness and metallic. numpy,
which Blender bundles, does the pixel work; everything runs on the main thread.
"""

import math
import re
from array import array

from mathutils import Vector

from ..core.scene import kept_texture
from ..core.scene.mesh_correspondence import MeshArrays

# Vertex groups of a head bone and its children: "Head", "head_end", "mixamorig:Head",
# "HeadTop_End", "DEF-head"; never "forehead".
HEAD_GROUP = re.compile(r"(?<![a-z])head", re.IGNORECASE)
# Empty texels within this many texels of a kept one, per 2048 of image size,
# take its colour, so mipmaps and filtering never mix in the result's colour.
GUTTER = 8
# Corners of one face on the same UV layout agree within this.
SAME_LAYOUT = 1e-4
# A colour read as a single value, as Blender converts it.
LUMINANCE = (0.2126, 0.7152, 0.0722)


def _numpy():
    import numpy

    return numpy


def _metres(scene):
    return scene.unit_settings.scale_length or 1.0


def _selected(mesh, numpy):
    flags = numpy.zeros(len(mesh.polygons), dtype=bool)
    mesh.polygons.foreach_get("select", flags)
    return flags


def selected_faces(obj):
    """Faces selected in Edit Mode on one mesh object, and its face count."""
    mesh = obj.data
    if obj.mode == "EDIT":
        # The mesh's own flags catch up only when Edit Mode is left.
        return mesh.total_face_sel, len(mesh.polygons)
    return int(_selected(mesh, _numpy()).sum()), len(mesh.polygons)


def standing(objects, scene):
    """Whether these objects' world bounds read as a standing character (cheap, for the form)."""
    corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not corners:
        return False
    size = [max(c[axis] for c in corners) - min(c[axis] for c in corners) for axis in range(3)]
    return kept_texture.standing(size, _metres(scene))


def starting_mode(objects, scene, keep_head):
    """The kept region a review of these objects starts on (cheap, for the form too)."""
    chosen = total = 0
    for obj in objects:
        count, faces = selected_faces(obj)
        chosen, total = chosen + count, total + faces
    return kept_texture.starting_mode(chosen, total, standing(objects, scene), keep_head)


def _head_bones(obj, numpy):
    """A rig's head weight per vertex, or None when no vertex group names a head bone."""
    groups = {group.index for group in obj.vertex_groups if HEAD_GROUP.search(group.name)}
    if not groups:
        return None
    weights = numpy.zeros(len(obj.data.vertices), dtype=numpy.float32)
    for vertex in obj.data.vertices:
        weights[vertex.index] = sum(item.weight for item in vertex.groups if item.group in groups)
    return weights


def _joined(targets, numpy):
    """The captured sources joined in scene coordinates, with selection and head weights."""
    positions, loops, starts, totals, selected, bones = [], [], [], [], [], []
    vertices = corners = 0
    rigged = False
    for target in targets:
        mesh, obj = target.mesh, target.obj
        co = numpy.empty(3 * len(mesh.vertices), dtype=numpy.float64)
        mesh.vertices.foreach_get("co", co)
        matrix = numpy.array(obj.matrix_world, dtype=numpy.float64)
        positions.append(co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3])
        corner = numpy.empty(len(mesh.loops), dtype=numpy.int32)
        mesh.loops.foreach_get("vertex_index", corner)
        loops.append(corner + vertices)
        start = numpy.empty(len(mesh.polygons), dtype=numpy.int32)
        mesh.polygons.foreach_get("loop_start", start)
        starts.append(start + corners)
        total = numpy.empty(len(mesh.polygons), dtype=numpy.int32)
        mesh.polygons.foreach_get("loop_total", total)
        totals.append(total)
        selected.append(_selected(mesh, numpy))
        head = _head_bones(obj, numpy)
        rigged = rigged or head is not None
        bones.append(head if head is not None else numpy.zeros(len(mesh.vertices), numpy.float32))
        vertices += len(mesh.vertices)
        corners += len(mesh.loops)
    join = numpy.concatenate
    co = join(positions)
    mesh = MeshArrays(
        array("f", co.astype(numpy.float32).tobytes()),
        array("i", join(loops).tobytes()),
        array("i", join(starts).tobytes()),
        array("i", join(totals).tobytes()),
    )
    size = (co.max(0) - co.min(0)).tolist() if len(co) else [0.0, 0.0, 0.0]
    return mesh, size, join(selected), join(bones) if rigged else None


def review(targets, mode, *, keep_head=True):
    """Resolve SELECTED, HEAD, NONE or AUTO on the captured sources, joined in scene space.

    AUTO starts on the selected faces when some but not all are selected, else on
    the head when `keep_head` is on and the sources read as a standing character.
    """
    numpy = _numpy()
    targets = tuple(targets)
    mesh, size, selected, bones = _joined(targets, numpy)
    if mode == kept_texture.AUTO:
        standing_mesh = kept_texture.standing(size, _metres(targets[0].scene))
        mode = kept_texture.starting_mode(
            int(selected.sum()), len(selected), standing_mesh, keep_head
        )
    return kept_texture.plan(
        mesh,
        mode,
        selected=selected.tolist(),
        head_bones=bones.tolist() if bones is not None else None,
    )


def _image_uv(node):
    """The UV map an image node reads ("" for the render UV map), or None when mapped otherwise."""
    vector = node.inputs.get("Vector")
    if vector is None or not vector.is_linked:
        return ""
    source = vector.links[0].from_node
    return source.uv_map if source.type == "UVMAP" else None


def _usable(image):
    # A generated image, such as one painted in Texture Paint and not saved yet,
    # reports type UV_TEST.
    return (
        image is not None
        and image.type in {"IMAGE", "UV_TEST"}
        and image.source in {"FILE", "GENERATED"}
        and image.size[0] > 0
        and image.size[1] > 0
        and image.channels >= 3
    )


def _image_from(socket):
    """The usable image node whose Color output feeds this socket directly, or None."""
    if socket is None or not socket.is_linked:
        return None
    link = socket.links[0]
    node = link.from_node
    if node.type != "TEX_IMAGE" or link.from_socket.identifier != "Color":
        return None
    if not _usable(node.image) or _image_uv(node) is None:
        return None
    return node


def _principled(material):
    if material is None or not material.use_nodes or material.node_tree is None:
        return None
    nodes = material.node_tree.nodes
    output = next(
        (n for n in nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output),
        None,
    )
    surface = output.inputs.get("Surface") if output is not None else None
    if surface is not None and surface.is_linked:
        node = surface.links[0].from_node
        if node.type == "BSDF_PRINCIPLED":
            return node
    return next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)


def material_maps(material):
    """{role: (image node, channels, colour)} read from a material's Principled BSDF.

    Base colour and normal maps feed it directly (normals through a tangent-space
    Normal Map node); roughness and metallic through a Separate Color channel, as
    a glTF metallic-roughness map does, or directly as a grey value.
    """
    bsdf = _principled(material)
    if bsdf is None:
        return {}
    maps = {}
    node = _image_from(bsdf.inputs.get("Base Color"))
    if node is not None:
        image = node.image
        maps["base_color"] = (node, (0, 1, 2), (image.colorspace_settings.name, image.is_float))
    normal = bsdf.inputs.get("Normal")
    if normal is not None and normal.is_linked:
        mapper = normal.links[0].from_node
        if mapper.type == "NORMAL_MAP" and mapper.space == "TANGENT":
            node = _image_from(mapper.inputs.get("Color"))
            if node is not None:
                maps["normal"] = (node, (0, 1, 2), None)
    for role, name in (("roughness", "Roughness"), ("metallic", "Metallic")):
        socket = bsdf.inputs.get(name)
        if socket is None or not socket.is_linked:
            continue
        link = socket.links[0]
        source = link.from_node
        if source.type == "SEPARATE_COLOR" and source.mode == "RGB":
            node = _image_from(source.inputs.get("Color"))
            channel = ("Red", "Green", "Blue").index(link.from_socket.name)
            if node is not None:
                maps[role] = (node, (channel,), None)
        elif (node := _image_from(socket)) is not None:
            maps[role] = (node, (0, 1, 2), None)
    return maps


def _uv_layer(mesh, name):
    if name:
        return mesh.uv_layers.get(name)
    return next((layer for layer in mesh.uv_layers if layer.active_render), None)


def _corner_uvs(mesh, name, numpy):
    layer = _uv_layer(mesh, name)
    if layer is None:
        return None
    uv = numpy.empty(2 * len(mesh.loops), dtype=numpy.float64)
    layer.data.foreach_get("uv", uv)
    return uv.reshape(-1, 2)


def _pixels(image, numpy):
    width, height = image.size
    data = numpy.empty(width * height * 4, dtype=numpy.float32)
    image.pixels.foreach_get(data)
    return data.reshape(height, width, 4)


def rasterize(points, width, height, numpy):
    """Texel centres inside each triangle: (triangle, x, y, barycentric weights).

    `points` holds (n, 3, 2) corner positions in texels. Triangles are grouped
    by bounding-box size so each group is tested on one grid of candidates.
    """
    found = ([], [], [], [])
    if not len(points):
        empty = numpy.zeros(0, dtype=numpy.int64)
        return empty, empty, empty, numpy.zeros((0, 3))
    a, b, c = points[:, 0], points[:, 1], points[:, 2]
    area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    low = numpy.maximum(numpy.floor(points.min(1) - 0.5).astype(numpy.int64) + 1, 0)
    high = numpy.floor(points.max(1) - 0.5).astype(numpy.int64)
    high[:, 0] = numpy.minimum(high[:, 0], width - 1)
    high[:, 1] = numpy.minimum(high[:, 1], height - 1)
    span = numpy.maximum(high - low + 1, 0).max(1)
    valid = (numpy.abs(area) > 1e-12) & (span > 0)
    previous, size = 0, 2
    while previous < span.max(initial=0):
        chosen = numpy.nonzero(valid & (span > previous) & (span <= size))[0]
        grid = numpy.arange(size)
        # Bound each batch to about 4 million candidate texels.
        batch = max(1, (1 << 22) // (size * size))
        for first in range(0, len(chosen), batch):
            index = chosen[first : first + batch]
            x = low[index, 0][:, None, None] + grid[None, None, :]
            y = low[index, 1][:, None, None] + grid[None, :, None]
            px, py = x + 0.5, y + 0.5
            ax, ay = a[index, 0, None, None], a[index, 1, None, None]
            bx, by = b[index, 0, None, None], b[index, 1, None, None]
            cx, cy = c[index, 0, None, None], c[index, 1, None, None]
            scale = area[index][:, None, None]
            w0 = ((bx - px) * (cy - py) - (cx - px) * (by - py)) / scale
            w1 = ((cx - px) * (ay - py) - (ax - px) * (cy - py)) / scale
            w2 = 1.0 - w0 - w1
            inside = (
                (w0 >= -1e-6)
                & (w1 >= -1e-6)
                & (w2 >= -1e-6)
                & (x <= high[index, 0][:, None, None])
                & (y <= high[index, 1][:, None, None])
            )
            t, row, column = numpy.nonzero(inside)
            found[0].append(index[t])
            found[1].append(x[t, 0, column])
            found[2].append(y[t, row, 0])
            found[3].append(
                numpy.stack([w0[t, row, column], w1[t, row, column], w2[t, row, column]], 1)
            )
        previous, size = size, size * 2
    if not found[0]:
        empty = numpy.zeros(0, dtype=numpy.int64)
        return empty, empty, empty, numpy.zeros((0, 3))
    return tuple(numpy.concatenate(part) for part in found)


def sample(pixels, uv, numpy):
    """Bilinear samples of (height, width, 4) pixels at UVs, repeating like a texture."""
    height, width = pixels.shape[:2]
    x = uv[:, 0] * width - 0.5
    y = uv[:, 1] * height - 0.5
    x0, y0 = numpy.floor(x).astype(numpy.int64), numpy.floor(y).astype(numpy.int64)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    x1, y1 = (x0 + 1) % width, (y0 + 1) % height
    x0, y0 = x0 % width, y0 % height
    return (
        pixels[y0, x0] * (1 - fx) * (1 - fy)
        + pixels[y0, x1] * fx * (1 - fy)
        + pixels[y1, x0] * (1 - fx) * fy
        + pixels[y1, x1] * fx * fy
    )


def _shifted(values, dy, dx, numpy):
    out = numpy.zeros_like(values)
    height, width = values.shape[:2]
    out[max(dy, 0) : height + min(dy, 0), max(dx, 0) : width + min(dx, 0)] = values[
        max(-dy, 0) : height + min(-dy, 0), max(-dx, 0) : width + min(-dx, 0)
    ]
    return out


def fill_gutter(pixels, covered, touched, margin, numpy):
    """Give empty texels within `margin` of touched ones a neighbour's colour, in place."""
    if not touched.any():
        return
    height, width = covered.shape
    steps = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    near = touched
    for _ in range(margin):
        grown = near.copy()
        for dy, dx in steps:
            grown |= _shifted(near, dy, dx, numpy)
        near = grown
    ring = numpy.flatnonzero(near & ~covered)
    if not len(ring):
        return
    flat = pixels.reshape(height * width, -1)
    filled = covered.ravel().copy()
    rows, columns = ring // width, ring % width
    pending = numpy.ones(len(ring), dtype=bool)
    for _ in range(margin):
        for dy, dx in steps:
            row, column = rows + dy, columns + dx
            inside = pending & (row >= 0) & (row < height) & (column >= 0) & (column < width)
            neighbour = numpy.where(inside, row * width + column, 0)
            ready = inside & filled[neighbour]
            if ready.any():
                flat[ring[ready]] = flat[neighbour[ready]]
                filled[ring[ready]] = True
                pending &= ~ready
        if not pending.any():
            break


def _channels(samples, result_channels, original_channels, numpy):
    """Original values for the result's channels: copied, spread from one, or read as grey."""
    if len(original_channels) == len(result_channels):
        return samples[:, list(original_channels)]
    if len(original_channels) == 1:
        return numpy.repeat(samples[:, list(original_channels)], len(result_channels), 1)
    grey = samples[:, list(original_channels)] @ numpy.array(LUMINANCE)
    return grey[:, None]


class _Source:
    """One retextured source: its triangles, kept weights and before/after meshes."""

    def __init__(self, target, weights, numpy):
        self.before, self.after = target.mesh, target.obj.data
        after = self.after
        after.calc_loop_triangles()
        count = len(after.loop_triangles)
        self.loops = numpy.empty(3 * count, dtype=numpy.int64)
        after.loop_triangles.foreach_get("loops", self.loops)
        self.loops = self.loops.reshape(-1, 3)
        self.polygons = numpy.empty(count, dtype=numpy.int64)
        after.loop_triangles.foreach_get("polygon_index", self.polygons)
        corner = numpy.empty(len(after.loops), dtype=numpy.int64)
        after.loops.foreach_get("vertex_index", corner)
        self.weights = weights[corner[self.loops]]
        self.before_slots = numpy.empty(len(self.before.polygons), dtype=numpy.int64)
        self.before.polygons.foreach_get("material_index", self.before_slots)
        self.after_slots = numpy.empty(len(after.polygons), dtype=numpy.int64)
        after.polygons.foreach_get("material_index", self.after_slots)
        self.uvs = {}

    def uv(self, side, name, numpy):
        key = (side, name)
        if key not in self.uvs:
            self.uvs[key] = _corner_uvs(self.before if side else self.after, name, numpy)
        return self.uvs[key]


def _material(mesh, slot):
    return mesh.materials[slot] if 0 <= slot < len(mesh.materials) else None


def composite(targets, region, created):
    """Paint each source's own maps back under its kept faces; return what was kept.

    Runs after RETEXTURE gave `targets` the result's UVs and materials, before
    the application is accepted: on a failure the caller rolls everything back.
    Only images in `created` (this application's new images) are changed.
    """
    summary = {
        "mode": region.mode,
        "source": region.source,
        "faces": region.faces,
        "maps": [],
        "skipped": {},
    }
    if not region.kept:
        return summary
    numpy = _numpy()
    created = {image.as_pointer() for image in created}
    weights = numpy.frombuffer(region.weights.tobytes(), dtype=numpy.float32)
    sources, offset = [], 0
    for target in targets:
        count = len(target.mesh.vertices)
        sources.append(_Source(target, weights[offset : offset + count], numpy))
        offset += count
    jobs, users, kept, skipped = {}, {}, set(), {}
    for index, source in enumerate(sources):
        after_slots = source.after_slots[source.polygons]
        for slot in numpy.unique(after_slots):
            maps = material_maps(_material(source.after, int(slot)))
            for node, _channels_used, _colour in maps.values():
                key = (node.image.as_pointer(), _image_uv(node))
                users.setdefault(key, []).append((index, numpy.nonzero(after_slots == slot)[0]))
        active = numpy.nonzero(source.weights.max(1) > 0)[0]
        if not len(active):
            continue
        pairs = numpy.stack([source.before_slots[source.polygons[active]], after_slots[active]], 1)
        for before_slot, after_slot in numpy.unique(pairs, axis=0):
            group = active[(pairs[:, 0] == before_slot) & (pairs[:, 1] == after_slot)]
            original = material_maps(_material(source.before, int(before_slot)))
            result = material_maps(_material(source.after, int(after_slot)))
            nodes = {}
            original_keys, result_keys = _keyed(original, nodes), _keyed(result, nodes)
            same = all(
                _same_layout(source, group, result_keys[role][0][1], original_keys[role][0][1])
                for role in ("normal",)
                if role in original_keys and role in result_keys
            )
            pairs_by_image, reasons = kept_texture.pair_maps(
                original_keys, result_keys, same_layout=same
            )
            for role, reason in reasons.items():
                skipped.setdefault(role, reason)
            for result_key, entries in pairs_by_image.items():
                if result_key[0] not in created:
                    for role, (key, _c, _k) in result_keys.items():
                        if key == result_key:
                            skipped.setdefault(role, "the result's map is not new")
                    continue
                for role, (key, _c, _k) in result_keys.items():
                    if key == result_key:
                        kept.add(role)
                for entry in entries:
                    jobs.setdefault(result_key, []).append(
                        (index, group, nodes[result_key], nodes[entry[1]], entry)
                    )
    for result_key, work in jobs.items():
        _paint(result_key, work, users.get(result_key, ()), sources, numpy)
    summary["maps"] = [role for role in kept_texture.ROLES if role in kept]
    summary["skipped"] = {role: reason for role, reason in skipped.items() if role not in kept}
    return summary


def _keyed(maps, nodes):
    """Key each role's image by (image, UV map), remembering the node behind each key."""
    keyed = {}
    for role, (node, channels, colour) in maps.items():
        key = (node.image.as_pointer(), _image_uv(node))
        nodes[key] = node
        keyed[role] = (key, channels, colour)
    return keyed


def _same_layout(source, group, result_uv, original_uv):
    numpy = _numpy()
    after = source.uv(False, result_uv, numpy)
    before = source.uv(True, original_uv, numpy)
    if after is None or before is None:
        return False
    corners = source.loops[group].ravel()
    return bool(numpy.abs(after[corners] - before[corners]).max(initial=0.0) <= SAME_LAYOUT)


def _paint(result_key, work, users, sources, numpy):
    """Composite every pairing that writes into one result image, then fill its gutter."""
    node = work[0][2]
    image = node.image
    pixels = _pixels(image, numpy)
    height, width = pixels.shape[:2]
    scale = numpy.array([width, height], dtype=numpy.float64)
    covered = numpy.zeros((height, width), dtype=bool)
    for index, triangles in users:
        source = sources[index]
        uv = source.uv(False, result_key[1], numpy)
        if uv is None:
            continue
        _, x, y, _ = rasterize(uv[source.loops[triangles]] * scale, width, height, numpy)
        covered[y, x] = True
    touched = numpy.zeros((height, width), dtype=bool)
    originals, raster = {}, {}
    for index, group, _result_node, original_node, entry in work:
        result_channels, _original_key, original_channels = entry
        source = sources[index]
        key = (index, id(group), _image_uv(original_node))
        if key not in raster:
            result_uv = source.uv(False, result_key[1], numpy)
            original_uv = source.uv(True, key[2], numpy)
            if result_uv is None or original_uv is None:
                raster[key] = None
                continue
            corners = source.loops[group]
            t, x, y, weights = rasterize(result_uv[corners] * scale, width, height, numpy)
            blend = (weights * source.weights[group][t]).sum(1)
            uv = (weights[:, :, None] * original_uv[corners][t]).sum(1)
            keep = blend > 1e-4
            raster[key] = (x[keep], y[keep], blend[keep], uv[keep])
        if raster[key] is None:
            continue
        x, y, blend, uv = raster[key]
        original = original_node.image
        if original.as_pointer() not in originals:
            originals[original.as_pointer()] = _pixels(original, numpy)
        values = _channels(
            sample(originals[original.as_pointer()], uv, numpy),
            result_channels,
            original_channels,
            numpy,
        )
        columns = list(result_channels)
        current = pixels[y[:, None], x[:, None], columns]
        pixels[y[:, None], x[:, None], columns] = (
            blend[:, None] * values + (1.0 - blend[:, None]) * current
        )
        touched[y, x] = True
    margin = max(2, math.ceil(GUTTER * max(width, height) / 2048))
    fill_gutter(pixels, covered | touched, touched, margin, numpy)
    image.pixels.foreach_set(pixels.ravel())
    image.update()
    # Pack the painted pixels losslessly: a JPEG would blur the kept maps, and a
    # file on disk keeps the result's own pixels.
    image.file_format = "OPEN_EXR" if image.is_float else "PNG"
    image.pack()
