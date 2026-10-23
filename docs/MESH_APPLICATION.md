# Explicit mesh application

`scenario.blender.mesh_application.apply_mesh` is a synchronous Blender main-thread
primitive for applying one already imported mesh to one explicit source object.
It has no network, import, job, UI or MCP side effects and never reads selection
to choose a target.

```python
receipt = apply_mesh(
    captured_scene,
    captured_source,
    imported_primary_mesh,
    policy="REMESH",  # or "UV" / "RETEXTURE"
    result_to_source=local_mapping,  # explicit finite, orientation-preserving affine 4x4 matrix
    keep_original=True,
)
# The caller owns the receipt until one of these explicit decisions:
receipt.accept()  # retain the application
# receipt.rollback()                # restore if both meshes are still unchanged
```

The caller must validate its captured file/scene/object revision immediately before
this call. It must also select the primary imported mesh and establish the mapping
from result mesh coordinates into source-local coordinates. Reflection and singular
mappings are rejected; there is no handedness/normal-flip policy. The primitive
does not infer that mapping from object placement, names or current selection.
It does not prove cloud provenance, safe download/import, or that a late result
still matches its original inputs. The
[verified saved-mesh command](#captured-source-and-verified-saved-mesh-command)
adds receipt-bound import, shared-session bookkeeping and UI/MCP review.

## Supported policies

| Policy | Geometry and attributes | UVs | Materials |
| --- | --- | --- | --- |
| `REMESH` | Copy result mesh and bake the explicit local mapping, or a [verified bounds fit](#bounds-fit-for-remeshes-and-copied-parts) | Adopt result UV layers | Adopt result mesh material slots and polygon assignments |
| `RETEXTURE` | Copy source geometry and non-UV attributes; require the [same surface](#surface-matching) | Replace all layers with result names, coordinates and active/render/clone roles | Adopt nonempty result slots and valid face assignments; preserve existing shader datablocks |
| `UV` | Copy source mesh; require the [same surface](#surface-matching) | Copy coordinates from exactly one result UV layer to the source's active layer; preserve its name and other layers; create a layer if absent | Preserve source slots and polygon assignments |
| `ANIMATE` (saved command only) | Unchanged, with its skin; [returned clips](#apply-returned-animation) are copied onto the rig that skins it | Unchanged | Unchanged |

A remesh deliberately replaces all source mesh attributes with the result's data.
Materials themselves remain
shared datablocks: their node graphs/images are never copied, mutated or reverted.
The source object's identity, name, local/world transforms, parenting, collection
membership, selection and object custom properties remain intact. Shared source
and imported-result mesh datablocks are never edited in place.

## Surface matching

UV, RETEXTURE, [RIG](#attach-a-returned-rig) and [PARTS split from the source's
faces](#apply-static-parts) keep the source geometry and read values from a
result that must be the same surface. Identical indexed topology
with exactly equal mapped positions is the fast path. Otherwise
[`mesh_correspondence.py`](../scenario/core/scene/mesh_correspondence.py) proves
the correspondence, which accepts what Blender's glTF export and providers do to
an unchanged surface: triangulation, vertices split at UV seams or sharp edges,
and reordered vertices and faces.

- Every result vertex must lie within the position tolerance of a source vertex.
  The tolerance is 1e-5 of the source's local size (the larger of its
  bounding-box diagonal and its farthest vertex from the object origin), widened
  to 1e-6 of the scene origin's distance in source-local units for objects far
  from it.
- Each result face must lie inside exactly one source face with the same
  winding. The result faces of each source face must tile it exactly: no
  missing, extra or overlapping faces. Coincident source vertices are told apart
  only by that face. Coincident faces of opposite winding, such as touching
  crate faces, are told apart by winding; those of the same winding are
  ambiguous and fail.
- Every split copy of one source face corner must carry the same UV within 1e-5
  (relative above 1). A seam inside a source face, such as across a quad's
  diagonal, cannot be represented on that face and fails. RETEXTURE also needs
  one material per source face; RIG needs the same bone weights within 1e-4 on
  every copy of a source vertex.
- Loose result vertices or edges fail. Loose source geometry has no face
  corners: UV and RETEXTURE keep it unchanged, and RIG fails because it gets no
  weights.

`apply_mesh` matches one result mesh in its own coordinates. `apply_surface`
matches several result objects as one surface, composing each object's world
matrix before the mapping, and records the verified `Surface` on the receipt:
its mapping, any fit base, and per-corner and per-face indices with the result
mesh each came from, for reuse by other policies.

`apply_surfaces` matches results against [several captured
objects](#several-captured-objects) at once. `match_sources` places each source
mesh by its world matrix and joins them into one surface in scene coordinates,
so the mapping takes result scene coordinates to the scene: the identity, or a
fit of it. Each source vertex keeps its own object's tolerance, scaled to scene
units, so objects far apart still match fine detail. The sources together, and
the results together, each stay within one object's component limit. Each source
takes its own corners, faces and vertices of the verified match; positions are
never copied back.

A failure names its counted reason, for example **UV result does not match the
source mesh: the result splits UV coordinates at 53 source face corners**. The
saved command reports it with the stopped application. Matching runs
synchronously on the main thread, within the mesh component limit.

### Bounds fit for remeshes and copied parts

A remesh, or parts that are not the source's own faces, is a different mesh of
the same surface, so faces cannot be matched. `mesh_application.fit_bounds`
verifies a fit by surface distance instead. Each base is first tried as it is,
so a result already at the source's size and place keeps it; only if no base
verifies does each get one uniform scale and offset from the axis-aligned
bounding boxes, never a rotation. Verification measures, in source-local units,
how far evenly sampled vertices lie from the other surface, both ways: result
vertices from the source surface, and source vertices from the placed result's
surface. At most 20,000 vertices per side are sampled, and only vertices that
faces use count. Distances are fractions of the source's bounding-box diagonal:

- at most 5% of either side's sampled vertices may lie farther than 2%;
- none may lie farther than 10%.

Copied parts may close each part with hidden contact or cap faces, so a part
vertex inside the source volume also passes: it lies behind the nearest source
face by that face's normal. This applies only to a source that encloses a volume:
after welding vertices at the same position, as UV and normal seams split them,
every face edge must meet its reverse in one other face and the signed volume
must be positive; otherwise part vertices must lie near the surface. Every
sampled source vertex must still lie near a part.

Provider remeshes measured within 0.7% of a source (1.8% for one delivered in
object-local coordinates), and remeshed parts with interior caps had 2.2% of
their vertices beyond 2% and none beyond 7.5%; a different object, or a result
fitted from the wrong base, had most of its vertices beyond 2%. The verified
worst distance and fraction beyond 2% are reported as `fit_residual`. If both
bases verify, they must place every result point within 2% of each other;
otherwise application stops. Surface queries use Blender's BVH tree on the main
thread, within the mesh component limit.

The source's active material index may be clamped by Blender when a remesh has
fewer slots. Rollback restores the original index only if the applied index is
unchanged; a later user change requires explicit review.

Only local, non-overridden meshes in Object Mode are supported. Modifiers,
constraints, vertex groups, shape keys, animation, armature/bone/vertex parenting,
vertex-parented children, object material overrides and custom mesh properties that
reference other data are rejected. Other custom mesh properties, such as the glTF
extras Blender imports, stay on the edited mesh under every policy; a result's own
are never adopted. Generic attributes are limited to boolean, scalar float/integer,
integer 2D, float 2D/3D and float/byte color types. Other types fail closed. The saved
command's [PARTS](#apply-static-parts) and [RIG](#attach-a-returned-rig) policies
cover segmented parts and compatible skins; RIG also accepts a source
[already skinned to an armature](#replace-an-existing-skin), and
[ANIMATE](#apply-returned-animation) copies returned clips onto that source's
rig. Several source objects are edited together only through the saved command's
[captured-source path](#several-captured-objects), for UV, RETEXTURE and RIG.
Supplying one explicit result object does not classify other returned helper
objects, maps or alternate meshes.

## Transaction and ownership

Staging copies and validates the candidate before swapping only `source.data`.
An exception during staging or publication restores the original pointer/material
index and removes only newly created staging objects/meshes. The original source,
imported result and downloaded files remain available for a local retry without
rerunning generation.

With **Keep original**, a duplicate object using the original mesh is linked into
the source's collections with the same parenting/transforms, hidden in the viewport
and renders so the edited mesh is what shows. It becomes user-owned
once returned, remains accessible as `receipt.original`, and survives both accept
and rollback. It shares the old mesh with any existing users; subsequent edits to
that old mesh prevent automatic rollback.

Without Keep original, a private unlinked object retains the original mesh until
the caller finalizes the receipt. `accept()` releases that holder and removes the
original mesh only if it has no remaining users and is unchanged. Shared meshes,
fake-user ownership, renamed meshes, new metadata and other edits are retained.
`rollback()` restores the original mesh and then releases the holder. A linked,
renamed, configured or otherwise adopted holder is retained for user review.
There is no destructor that accesses Blender. Callers must finalize their
receipts; this is an in-memory transaction boundary, not persisted recovery or
integration with Blender's global undo stack. File loading, undo that removes
datablocks and source deletion can make a receipt unusable; it never re-finds
targets by name.

Rollback rechecks the supported object structure as well as source/scene membership,
the applied mesh pointer, active material selection and fingerprints of both original
and applied meshes. Adding modifiers, constraints, vertex groups, shape keys,
animation, incompatible parenting or object material overrides requires explicit
review before rollback. These guards protect topology-dependent data and metadata
outside the fingerprint. A refusal leaves the receipt open; removing the added
structure allows retry if the remaining guards still pass. The fingerprints cover
geometry, supported generic attributes, UV layer roles, material slot bindings and
custom mesh properties, so editing the applied mesh in place cannot silently
lose user work. Shader node graph edits are outside that fingerprint and are
never reverted. Rollback removes its unchanged staged mesh only when no other
user owns it; it never removes the imported result or a mesh adopted by another
object.

Fingerprinting is linear and runs on the main thread. A limit of 2,000,000 combined
vertices, edges, loops, polygons and generic-attribute entries bounds each pass;
this is a work cap, not a latency guarantee. Large meshes and unsupported data
require another application path. A [skinned](#replace-an-existing-skin) mesh over
the cap is captured without its geometry and weights, and only ANIMATE, which
changes neither, applies to it.

## Explicit saved GLB import

The shared saved-job path can import one explicitly selected GLB result
(`model/gltf-binary`, or its `model/glb` alias) into a new **Scenario Model**
collection and parent group. It places the model's world-space bottom center at
the approved 3D cursor, retains the imported hierarchy and materials, packs
embedded images, and leaves existing objects, selection, active object and
viewport shading unchanged. It does not replace an existing source mesh or
implement the edit policies above. Alternate result files and maps remain saved;
only the selected GLB is imported. One import consumes the job's application
claim.

[`glb.inspect_glb`](../scenario/core/scene/glb.py) checks the
[GLB 2.0 container](https://github.com/KhronosGroup/glTF/blob/98015344c6a5f5a3a96686cbd77960a8b09f6276/specification/2.0/Specification.adoc)
and the supported import policy before Blender runs. It requires one scene,
one embedded binary buffer and no URI references. The buffer's `byteLength` may
be shorter than its binary chunk: Viggle Text to Motion leaves unused bytes after
the buffer, which glTF validators only warn about and importers never read; a
buffer longer than its chunk is refused. New-group imports retain skins
and node transform/morph-weight animations. Limits are 256 MiB of file bytes,
8 MiB of JSON, 10,000 nodes, 10 million accessor entries, 128 skins, 128 animation
clips and 10,000 total joints or animation channels. This is a bounded policy
preflight, not a complete glTF validator or proof against every expensive decoder
input; Blender validates geometry and textures. JSON glTF, FBX, OBJ and mesh PLY
results import through the [saved package path](#saved-model-package-import), and
SPZ, `.splat` and Gaussian splat PLY results through
[saved Gaussian splat import](#saved-gaussian-splat-import). Multiple scenes,
external files and pointer-based animation remain unsupported. Unsupported
downloads remain available. REMESH, UV, RETEXTURE and PARTS keep the default
static-only preflight; RIG and ANIMATE use the bounded skin policy below. Film
shots still accept only `model/gltf-binary`; in-place edits stage a GLB, JSON
glTF, FBX or OBJ
[import unit](#captured-source-and-verified-saved-mesh-command).

[`model_application.apply_model`](../scenario/blender/model_application.py),
which Film shots use, rehashes the exact local receipt, writes a private snapshot
and imports into a disposable scene with scene extras and selection changes
disabled. The saved-job command reaches the same importer through the package
path below, so its GLB preflight runs before the claim. Publication
moves only the new objects into a new destination group. Embedded images remain
packed after temporary files are removed. Failures remove only newly created
data and verify the final datablock sets, including staging scenes and shape keys.
Incomplete scene cleanup remains uncertain instead of authorizing another import;
there is no receipt-only retry when scene success is unknown. Temporary snapshot
cleanup is attempted separately: a filesystem cleanup error reports a sanitized
warning and may leave a temporary file, but preserves a completed packed import.
Copying, hashing and decoding are synchronous on the main thread, so large models
can pause Blender. There is no automatic blend save.

Native **Import GLB model (N)** or **Import alternate: GLB (N)** and MCP
`prepare_result_application` with the unit's `asset_id` capture the scene
revision and exact cursor. MCP `target_size_m`, or the native review's
**Longest side** option, binds a length to the approval:
publication then scales the group root uniformly so the longest side of the mesh
bounds, measured like the bottom center, has that length, and keeps the bottom
center at the cursor. The native review of a mesh unit from a job with one
uploaded mesh source still live in the scene can instead match it: the length
is that source's longest side and the bottom center lands on its bottom center.
A model with no measurable size fails after the claim and is rolled back. Every
import reports the group's measured world size and bottom height in MCP
`model_import`. Approval is consumed once; worker verification,
destination revalidation and the main-thread snapshot preflight precede the
durable claim. The current scene must be local and in Object Mode both at
preparation and after verification. Rejection before the claim, including a
receipt that changed after verification or a GLB that fails its preflight,
leaves a ready job ready and a completed job without a new local claim. Only a
failure after the claim records a failed application.
A moved cursor, changed scene/file/context or stored revision requires review
again. Completed jobs can import another saved model under a separate local
claim after fresh approval. An interrupted original or local `applying` claim
cannot be replayed.
Receipt-only retry saves known success without importing another model, and
session shutdown releases that retry handle.

### Native undo for saved model imports

The import runs on Blender's main thread after worker verification, outside any
native operator, so Blender records no operator Undo step for it. The model
command therefore records Blender history itself, under the same conditions as
[saved mesh edits](#native-undo-for-saved-mesh-edits): a desktop window, Global
Undo enabled and at least two undo steps. The extension does not change
preferences, and background application creates no desktop history.
`import_snapshot` records both checkpoints for every saved model format, and
`import_splat` records the same two for saved splats. The first, **Before
Scenario model import**, follows the snapshot preflight or worker splat
preparation, the claim and destination revalidation, and precedes staging or the
point build. It holds the latest scene, including changes no operator recorded.
The second, **Scenario model import**, follows publication and staging scene
removal. Neither contains the staging scene. One Undo removes only the new group
and its data and keeps the user's
earlier steps; Redo restores the group. Only the saved-result command records
these checkpoints. A Film shot build imports its heroes through `apply_model`,
which records none, so history never holds a partially built shot; the build
keeps its own Undo behavior.

A failed initial checkpoint stops before staging. The claim then fails like other
known import failures, so the job can be reviewed again. A failed final checkpoint
leaves the completed import applied and logs a sanitized warning; it never
authorizes another import. A failed import after the initial checkpoint is rolled
back, and that checkpoint stays in history; the command never calls Undo itself.
Undo/Redo changes Blender scene data only. The saved job stays applied, spending
records are unchanged and Redo does not import or generate again. Importing again
after Undo requires fresh reuse approval under a separate local claim.

## Rigged and animated model import

The new-group path keeps imported armatures, bone hierarchy, vertex weights,
shape keys, actions and NLA clips. Blender activates the first clip and retains
other clips in muted NLA tracks. Animation times use the destination scene's
current effective frame rate; time zero maps to frame zero. Placement anchors the
first clip's frame-zero bottom center at the approved cursor, measured in the
disposable staging scene before publication. The destination's current animated
pose does not change that anchor. Import leaves the
current frame/subframe, frame range and frame rate unchanged. It does not shift
clips to the current frame, extend the timeline or retarget animation to an
existing rig ([ANIMATE](#apply-returned-animation) does that for a matching or
humanoid skeleton). Moving the new parent group moves the imported character together.

Armature construction requires the staging scene to own the active window and
view layer while Blender's importer runs. The importer restores both afterward,
including on failure, and disables generated bone-display helper geometry.
Blender's glTF importer divides its guessed bone lengths by the armature object's
scale, so a centimetre skeleton under a 0.01 scale, as Meshy Rigging returns,
would draw bones a hundred times too long, In Front of the character.
Each imported armature is redrawn at the character's size instead: a bone reaches
its nearest child, a leaf takes its parent's length, none passes half the
skeleton, and In Front is off. Only lengths change, never heads, directions or
rolls, so rest matrices, weights, poses, clips and retargeting stay as imported;
a bone with a connected child or B-Bone segments keeps its length. An object
parented to a bone lands where the file puts it.
Ordinary background Blender sessions retain an off-screen window and support
that path. An explicitly windowless caller can import static models or apply a
saved static mesh using its scene and view layer; rigged models are rejected
before importer execution when no window is available.
It also restores the optional glTF animation UI list on pre-existing scenes:
that upstream UI writes outside the import context. Imported actions and NLA
tracks remain on their new owners. Supported Blender 5.0/5.1/5.2 importers multiply
seconds by `fps * fps_base`; the disposable scene uses reciprocal `fps_base` so
clips match the destination's effective `fps / fps_base` without changing its
settings.

This imports a complete new character. The separate [RIG policy](#attach-a-returned-rig)
can attach a compatible returned skin to a captured static mesh; retargeting an
existing rig remains outside this import command. This new-group command records
the same [native Undo steps](#native-undo-for-saved-model-imports) as a static
import. See [animated import interaction](ui/saved-3d.md#animated-model-import-interaction).

## Saved 3D package classification

[`model_formats.classify_packages`](../scenario/core/scene/model_formats.py)
groups a saved job's results into ordered import units without Blender, files or
network access. The [saved package import](#saved-model-package-import) offers and
claims these units. In-place mesh edits apply a GLB, JSON glTF, FBX or OBJ unit
by the same key and name it primary or alternate; the Film path does not use
them.

Inputs are URL-free manifest facts typed by the pinned SDK 2.3.0
[asset response](https://docs.scenario.com/api/python/resources/assets/methods/retrieve):
`mimeType`, the verified receipt size (else `properties.size`), the stored texture
role, and the lineage facts `metadata.type` and `metadata.parentId`. MIME selects
handling. `model/gltf-binary` and `model/glb` are GLB, `model/gltf+json` is JSON
glTF, and `model/x-fbx` plus the two Autodesk `application/*` FBX types are FBX.
OBJ, PLY (`model/ply`, `application/x-ply`), SPZ and `.splat` complete the supported
set; `model/mtl` is only an OBJ companion. Other `model/*` types, such as ksplat,
sog, STL and USD, are reported as unsupported. `check_signature` confirms that
leading bytes match the declared format (binary FBX, gzip or `NGSP` SPZ, whole
32-byte `.splat` records); it never chooses a format by content.

With lineage, an OBJ binds its single MTL child and one map per slot (albedo or
base, normal, roughness, metallic) among the OBJ's or that MTL's children, so
several OBJ packages in one job stay separate. A model file among those children
is its own unit, never a companion. Without lineage, an OBJ or glTF binds
companions only when it is the job's only file of that format, oversized ones
included. Several MTLs, several maps for one slot, maps without a material,
unsupported formats and oversized files remain saved and are reported with
stable reason codes; nothing is guessed. Once a job holds any model file (a
`model/*` type, an MTL included, an FBX `application/*` type or
`application/x-ply`), every saved file is in exactly one place: one unit's
files, one glTF unit's candidate resources, which are bound later by reference,
or one finding. A file with a finding is never also a companion or a candidate
resource. Without lineage, an MTL or slot map beside several OBJs, or a buffer
or image beside several glTFs, is reported as `ambiguous-package`. Any other
leftover is `unbound`, such as a map whose stored role (smoothness, height, ao
or edge) has no MTL slot, a map beside a sole OBJ that is too large or, with
lineage, a file under a skipped or unsupported model, whose own finding gives
the cause. A job without a model file gives an empty plan. With lineage,
generated root outputs sort first: a `metadata.type` of `img23d`, `txt23d`,
`3d23d`, `video23d` or `img2splat` whose parent is not in the job. Then GLB,
glTF, FBX, OBJ, mesh PLY, SPZ, splat or unclassified PLY and `.splat` follow.
Ties prefer more bound companions, then the larger file, then manifest order. The
first unit is primary and the others are alternates for explicit selection.
`inspect_ply_header` treats a binary little-endian PLY with float `x`, `y`, `z`,
`f_dc_0..2`, `opacity` and `scale_0..2` vertex data, no faces and, when known, an
exact body size as a Gaussian splat; other well-formed PLYs are meshes. Header lines
end at LF only, structural lines are printable ASCII, element names are unique and
property names are unique within an element. Limits are 256 MiB per file, 512 MiB
per package, 4 MiB per MTL, 8 MiB of glTF JSON and 64 KiB of PLY header.

[`model_references`](../scenario/core/scene/model_references.py) plans the private
snapshot. Each unit lists canonical file names such as `model.obj`, `material.mtl`
and `texture-albedo.png`. `rewrite_obj` streams an OBJ, points its first
`mtllib` at the bound material and removes other libraries and file-reading
statements. `rewrite_mtl` points `map_Kd`, `map_Pm`, `map_Pr` and
`map_Bump`/`bump`/`norm` at bound textures, keeps only `-o`, `-s` and `-bm`
options whose values are plain ASCII decimal numbers and drops every other map,
`refl`, `disp` and `decal` statement, including maps whose files are not part of
the saved package. Blender reads a value such as `1_0` as part of the file name,
so any other value ends option parsing and the option is dropped. A bound normal
statement without a kept `-bm` gets `-bm 1`: Blender's OBJ importer sets its
Normal Map node's Strength from `-bm` and uses 0 without one. A slot whose
materials name different files is dropped rather than shared. Original names,
absolute paths, traversal and URLs never reach the output. Reports keep the
line, a fixed keyword and the reason, never the reference: an unknown keyword
reports only its matched prefix, such as `map_`, because a reference can be
glued to it.

Text must use LF or CRLF endings without NUL bytes, and every physical line is
classified on its own. Blender's MTL reader has no line continuation, so a trailing
backslash never hides the next MTL line from the rewrite. An OBJ statement continues
after a backslash and optional whitespace, as Blender reads it. A continued OBJ
statement is rejected when any of its physical lines starts with a file-reading
keyword, because Blender 5.0 and 5.1 can read a continuation line by itself at a
read-buffer boundary. OBJ streaming checks cancellation every 65,536 lines and every
4 MiB read. `inspect_gltf_json` applies the GLB document bounds and keeps base64
data URIs with a supported media type, also when RFC 2397 `attribute=value`
parameters precede `;base64`; a unit test keeps its duplicated document checks
aligned with `inspect_glb`. It binds an external buffer by asset-ID file stem or
by a unique exact size, and an external image only by asset-ID stem; any other
URI, including one inside an extension, fails closed. Buffers and images bind
separately, and every buffer's saved size must equal its own `byteLength`, also
when several entries share a URI. All functions take bytes or streams, so
integration can prepare snapshots on a worker from verified copies. The
importer's own file search stays inside the snapshot only if every canonical
name passed to these functions is written into the snapshot before import:
Blender looks for a missing file elsewhere, including the process working
directory. The import must still check the images it creates.

Schema 12 stores each result's in-job parent as `parent_id`
([result parents](JOB_STORAGE.md#result-parents)), but the classifier does not read it
yet. Its lineage rules expect an OBJ's MTL and maps under the OBJ; live Meshy results
put them beside it, under the GLB. Until binding by parent lands
([#609](https://github.com/scenario-labs/blender-plugin/issues/609)), every stored
manifest uses the stricter rules without lineage;
`members_from_results` accepts lineage only as an explicit mapping, so parent
binding and generated-output ordering apply only when a caller supplies it.
Undocumented provider file names are never used. Provider package shapes, SPZ
versions and glTF delivery need live evidence, and this primary/alternate
ordering labels results but never chooses an edit policy.

## Saved model package import

A saved job's GLB, JSON glTF, FBX, OBJ and mesh PLY import units can each be
imported as a new **Scenario Model** group at the approved cursor. Native saved-job
controls list one **Import <format> model (N)** button for the primary unit and
**Import alternate: <format> (N)** for the others, in the classified order; N
counts every saved file. MCP `job_status` reports every unit in `import_units`,
with `importable`, `primary`, its members and roles, glTF candidate resources and
`import_findings` for files left out. SPZ and `.splat` units are offered as
splats, and a PLY unit is a mesh or splats depending on its bytes; both follow
[saved Gaussian splat import](#saved-gaussian-splat-import). Nothing is imported
automatically.

The review captures the scene revision and cursor like the GLB command above. The
dialog and MCP approval name the format, the saved files (for example
`OBJ + MTL + 2 maps`), primary or alternate, and format-specific limits. After
worker verification, [`prepare_snapshot`](../scenario/blender/model_application.py)
runs on the main thread before the claim. It opens every member without following
links, requires the exact receipt size and SHA-256, and writes canonical names into
a private directory under the extension's user `model-import` folder:

- GLB is checked by `inspect_glb`; JSON glTF by `inspect_gltf_json`, which binds
  buffers and images only to this job's saved files and rewrites their URIs.
- OBJ is streamed through `rewrite_obj` and its bound MTL through `rewrite_mtl`;
  every map the MTL can reference is copied beside it. Missing or unsupported
  references are dropped and counted.
- FBX must be binary and needs Blender's bundled FBX add-on; a disabled add-on
  stops before any file is written.
- PLY reaches this step after worker preparation found no splat data, or after
  ordinary verification while the local-operation slot was busy; the snapshot
  applies the same `splat_ply` rule again, and a Gaussian splat PLY stops here
  with the saved file kept and a request to review the import again once the
  local operation finishes.
- Map and glTF image bytes must start like PNG, JPEG or WebP.

A failure removes the snapshot and raises before the claim: the saved job, its
local application list and the scene are unchanged, and the Jobs row says
**Nothing was imported** with the reason. Blender's FBX, OBJ and PLY operators
need a window context, as do rigged glTF imports, so an explicitly windowless caller
is rejected at this step; ordinary background sessions keep an off-screen window.
Snapshot copying and hashing are synchronous on the main thread, bounded by 256 MiB
per file and 512 MiB per package.

The claim follows, as for GLB: a ready job's claim covers the whole job, and a
completed job's reuse claim names every member read, unit key first. Then
`import_snapshot` imports into a disposable staging scene. glTF and GLB use the
importer and timing above. FBX uses the bundled `import_scene.fbx` without image
search, OBJ uses `wm.obj_import` with mesh validation and both make imported
material names unique. PLY uses `wm.ply_import`. Selection made by these
importers stays in staging. Every new image must be packed by the importer
(embedded FBX or glTF data) or load from the snapshot directory itself; anything
else, including an FBX texture at an absolute path or an OBJ placeholder, fails
the import and rolls back. Blender's OBJ importer reads every MTL map as sRGB,
so the unit's saved texture roles decide: bound normal, roughness and metallic
maps become Non-Color data while albedo stays sRGB, and a normal map that does
not already reach the shader through a Normal Map node gets one. The importer's
node takes its Strength from the rewritten `-bm`, so a saved MTL without one
gets full strength, as in the GLB. Accepted images are packed and their file
paths cleared. The FBX importer sets the file's frame rate on the staging scene:
clips keep that timing and the destination scene keeps its own. When they
differ, `model_import.frame_rate_mismatch` is true and the job row shows **Clips
keep the file's frame rate, which differs from the scene's**. Publication
matches the GLB group and records `scenario_assets` with the member list on the
root.
Failure removes only new objects, meshes, materials, images, curves, textures,
actions and the staging scene, then verifies the datablock sets. Receipt-only
retry, reuse claims and session cleanup are shared with the GLB path. MCP status
keeps a session-local `model_import` summary (unit, format, members, dropped
references and frame-rate mismatch) until undo history changes. Newly downloaded
`model/glb`, Autodesk FBX `application/*` and `model/mtl` results keep `.glb`,
`.fbx` and `.mtl` local name extensions instead of `.bin`; saved names never
change, and import uses canonical snapshot names, not local ones.

## Saved Gaussian splat import

SPZ, `.splat` and PLY import units are read by a worker before any claim. The
review offers **Import splats: SPZ (N)** or **Import splats: .splat (N)**
(**Import alternate splats: ...** when the unit is not primary); a PLY keeps
**Import PLY model (N)** because only its bytes say whether it is a mesh. The
approval captures the scene revision and cursor like the other model imports
and adds two reviewed options: a point limit of 250,000, 500,000, 1,000,000
(default) or 2,000,000, and the saved axes, `OPENGL` (right, up, back) or
`OPENCV` (right, down, forward). The default axes are the file format's
convention from [worker-side splat preparation](RESULT_TRANSFERS.md#worker-side-splat-preparation):
`OPENGL` for SPZ and `OPENCV` for PLY and `.splat`. Providers can store worlds in
other axes, so these defaults are not established by live visual evidence yet.
Changing an option in the native dialog exchanges the approval for a new handle
under the same scene, cursor and unit (`revise_model_application`); the old
handle stops working. MCP prepares a new approval instead.

Application queues `JobSession.prepare_model_import` in the single local-operation
slot shared with local renders and Film media inspection; a busy slot rejects an
SPZ or `.splat` import before any work, with the saved job unchanged and the
approval consumed, so review the import again later. The native dialog reports
that reason. A PLY needs the slot only to decode splats: while it is busy, the
PLY queues ordinary verification instead and imports through the mesh snapshot
path when its verified header shows a mesh, while splat data stops with
**Nothing was imported** before any claim and asks for a new review once the
local operation finishes. The worker verifies every
receipt again and decodes the selected file while hashing it, with the approved
options. A decoder rejection (for example SPZ v4, the pre-release v1 or a
compressed PLY), a changed file or cancellation reaches the job row and MCP
`error` as **Nothing was imported:** with the reason, before any claim. A PLY
without splat data comes back without points and continues through the
[mesh snapshot path](#saved-model-package-import). On the main thread,
`apply_recovered_model` accepts only the preparation of the approved unit with
exactly the approved options, claims it like other model imports (a reuse claim
names the unit key) and calls [`splat_application.import_splat`](../scenario/blender/splat_application.py).

The builder never reads files and never runs an importer. It creates a new mesh
whose vertices are the kept splat centres, with `splat_color` (display-referred
RGB and opacity), `splat_opacity` and `splat_radius` point attributes written from
the decoded buffers. A new Geometry Nodes group, **Scenario Splat Points**, turns
the vertices into points with Mesh to Points: the radius is `splat_radius`
times a **Point scale** input (1.0), capped by a **Max radius** input that
starts at the 99th percentile of an even sample of at most 10,000 radii, so rare
huge splats cannot hide the cloud. Both inputs stay editable on the modifier. A
new unlit material shows the colour through an Emission shader, after a 2.2
gamma that approximates the sRGB to linear conversion, mixed with Transparent by
opacity. Mesh plus Geometry Nodes is used because `PointCloud.resize` is missing
in Blender 5.0. Every datablock is new: an existing material named **Scenario
Splat** or node group named **Scenario Splat Points** is never reused or
changed. Publication reuses the model group: a new **Scenario Model** collection
and root with the bottom center of the decoded bounds at the cursor,
`scenario_asset` and `scenario_assets`, and `scenario_splat_points` and
`scenario_splat_kept` counts. A reviewed longest side fits the longest side of
those decoded centre bounds, so the reported size, which includes point radii,
can be slightly larger. Selection, the active object and the timeline stay
unchanged. A failure removes only new objects, collections, meshes, materials
and node groups, then verifies those sets; incomplete cleanup is reported as
uncertain, and receipt-only retry never builds the points again. In desktop
Blender the import records the
[native Undo steps](#native-undo-for-saved-model-imports) of a model import, so
one Undo removes only the new group.

This is a point-cloud approximation, not a Gaussian splat renderer: there are no
rotations, anisotropic scales, view-dependent colour or sorted alpha blending,
and each splat becomes one sphere. Denser files are thinned evenly. MCP
`model_import.splat` reports `points_total`, `points_kept`, `step`, `axes` and
`spz_extensions` until undo history changes, and the native job row shows
**Shown as points: K of N splats**. When an SPZ header declares extensions, which
can include a coordinate-system record that is not read, the row also says
**This SPZ declares extensions; check its axes**. Provider files, default axes,
viewport performance at 1,000,000 or more points and physical desktop review need
live evidence.

## Captured source and verified saved-mesh command

`mesh_application.capture_target(scene, source)` freezes the live source object,
mesh, names, bounded geometry/attribute fingerprint, transforms, parenting,
collection membership and active material index. It accepts one local scene in
Object Mode and retains the primitive's unsupported-data checks, except that a
source [skinned to an armature](#replace-an-existing-skin) is captured with its
skin. Only RIG and ANIMATE accept that target; the other policies reject it
before import because they would drop the skin. It does not infer selection.
Capture evaluates the current view layer so pending parent transforms cannot
hide behind a stale world matrix. `validate_target` rejects intervening edits,
replacement, deletion or membership in another scene. Capture the mesh snapshot
first, then the `JobSession` origin, before asynchronous work; a target captured
afterward cannot establish the old input's identity. Restart/file load requires
a fresh explicit destination review.

`mesh_result_application.prepare_saved_mesh(target, unit, files, policy=...,
result_to_source=..., keep_original=...)` and
`apply_saved_mesh(target, snapshot, ...)` connect the existing primitive to one
verified [import unit](#saved-3d-package-classification) of the saved job,
chosen by its key: a GLB, JSON glTF, FBX, or OBJ with its MTL and maps. The
preparation checks the request, then runs the
[package snapshot](#saved-model-package-import) preflight before any claim:
receipt rehash, private snapshot with rewritten references, format checks and
the window requirement of the FBX and OBJ importers and of rigged glTF. A
changed or unsupported result raises `ModelPreflightError` with the saved job
and the scene unchanged, and the Jobs row says **Nothing was applied** with the
reason. Splat units are never applicable, and PLY units are left out because
only the worker import path reads whether their bytes hold a mesh. Application
stages the snapshot with the package importers, texture roles and image packing
in an isolated staging scene. For static policies FBX clips are not read; RIG
and ANIMATE read them at the file's frame rate, never retimed, and
`mesh_edit.frame_rate_mismatch` and the same job row report a different scene
rate. `REMESH` requires static meshes with optional Empty parents. Several
meshes, as some providers return a remesh split into pieces, are joined into
one: each object's world matrix is applied and material slots are merged once
per material (`joined_meshes` counts them). Joining needs Fit and verify, and
stops when two meshes each have over half of their sampled vertices within 2% of
the smaller one's size from the other's surface, as levels of detail or variants
in one place do. `UV` and `RETEXTURE` match every static mesh in the result
together as one surface, since providers split results by connectivity or color
region; RETEXTURE merges their material slots, once per material. The explicit
`PARTS` policy accepts 2 to 128 static surface meshes in that one result; other
object types fail for these static policies. RIG requires one armature, optional
Empty parents and skinned meshes, matched together as one surface. A mesh an
imported armature uses as a bone custom shape is a display helper: it is not
counted as a result mesh and is removed with the other imported objects (the
importer is told not to create these). Every other mesh counts, so an unskinned
mesh beside the skin, which may be an accessory, makes RIG refuse the result
instead of discarding it. A clips-only result, whose rig drives no mesh, fails
the skin checks. A skinned bone-display mesh cannot be told from a character and
fails the surface match. ANIMATE requires one armature with clips; returned
meshes, helpers and Empties are allowed but never kept. The caller chooses the
policy and Keep original. Multiple result assets are never combined or ranked
automatically.

The required finite, orientation-preserving mapping converts **Blender-imported
result scene coordinates** into **source-local coordinates**. Imported node
transforms are composed into it after the importer's axis and unit conversion:
glTF Y-up becomes Blender Z-up, an OBJ is read Y-up with -Z forward (the same
convention, so an OBJ and a GLB of the same coordinates land in the same place),
and an FBX uses the axes and unit scale it declares, which stay on the imported
objects (a centimetre file imports at 0.01 scale). A strict mapping is
used as given, and the source object never moves. UV, RETEXTURE and RIG also
require [surface matching](#surface-matching) after mapping; UV needs one UV
layer on each result mesh.

For every policy except ANIMATE the caller may instead pass an approved
`mesh_application.FitRequest` of base mappings, normally scene (`WORLD`) and
object-local (`LOCAL`). A base under which the result has identical indexed
topology and equal positions, unfitted or then fitted, is used at once. For each
base, the command estimates one uniform scale and offset that take the result's
axis-aligned bounding box onto the source's, with rotation fixed. UV, RETEXTURE,
RIG and parts split from the source's faces then run the full surface match with
the usual tolerance. A base fitted to within a tenth of the tolerance of an
earlier one reuses its match. One verified base is used; two are used only if
they assign every result corner and face identically. REMESH and copied parts
use the [bounds fit](#bounds-fit-for-remeshes-and-copied-parts). Rotation is
never searched: a fit changes only size and position. Otherwise application
stops before mutation, naming each base's reason. The returned application and
`mesh_edit` status report the verified mapping (`result_to_source`), the base it
was fitted from (`fitted_from`, null for a strict mapping) and, for a bounds
fit, `fit_residual` (`max_distance` and `beyond_tolerance`, fractions of the
source size; null otherwise). PARTS also reports `parts_from` and REMESH
`joined_meshes`.

The source is revalidated immediately before replacement. Temporary imported
objects are removed; RIG retains its armature/parent hierarchy and ANIMATE only
its copied clips. Replacement
material/image dependencies remain packed. Keep original
retains a separate hidden, unselected copy, preserving the previous selection and active
object. Without it, the primitive may release the unchanged, unused original mesh.
A returned result is finalized and contains the source, optional original and
policy and whether a desktop undo checkpoint was recorded; it is not a persistent
rollback handle. See [native history](#native-undo-for-saved-mesh-edits).

Successful cleanup sweeps unused imported datablocks across the shared importer's
categories, including helper actions, while retaining existing data, live
dependencies and fake-user ownership. Groups are released before their images.
Animated or skinned GLB and glTF results are rejected by preflight before the
claim for static policies. Morph targets can decode,
but the mesh policy rejects their shape keys; removing the imported mesh also
removes its keys. A confirmed failure permits a newly reviewed local attempt only
after exact datablock restoration.

On failure after replacement, the command attempts guarded rollback before any
new-data cleanup. It permits a known local failure only after both the exact
captured source and original datablock sets are restored. An edited source,
failed rollback or incomplete cleanup remains uncertain; new data is retained
when removing it could destroy a possibly applied result. A temporary-file cleanup
warning does not undo a completed packed result.

`JobSession.apply_recovered_mesh` supplies owner-issued verification, exact
scene/object origin resolution, the snapshot preflight and a durable claim
before mutation. Original ready/confirmed-failed jobs use their recovered claim;
completed jobs use a separate `mesh_edit` local claim whose destination
identifies the source object and that names every member read, unit key first.
Several captured sources claim their scene instead; the job's saved mesh-source
binding lists those objects in order. `retry_model_receipt` records only known
success, never another replacement. See [session
ownership](BLENDER_JOB_CONTEXT.md#verified-saved-mesh-replacement). The command
makes no service request. ANIMATE retargets clips between
[humanoid skeletons](#retarget-a-humanoid-clip) only.

## Saved mesh edit approval

**Apply mesh edit (N)** and MCP `prepare_result_application` with
`purpose: mesh_edit` review one saved GLB, glTF, FBX or OBJ import unit against
the currently active mesh. The review names the scene, source and selected
asset, its format and whether it is the job's primary or an alternate result, as
[classified](#saved-3d-package-classification). A primary GLB's control reads
**Apply mesh edit (N)**, another primary format names it, as in **Apply mesh
edit: FBX (N)**, and an alternate reads, for example, **Apply alternate mesh
edit: OBJ (N)**. MCP returns `format` and `primary`. `REMESH` replaces geometry,
UVs and mesh materials; `UV` replaces only active UVs of the
[same surface](#surface-matching); `RETEXTURE`, `PARTS`, `RIG` and `ANIMATE` are
described below. **Keep original** defaults to enabled.

The default edit follows the job's Edit 3D task
([`mesh_edit_policy`](../scenario/core/scene/mesh_edit_policy.py)): the task
this session submitted the job with when that task lists its model, otherwise
the model's only task in the Edit 3D lists. Remesh, Retexture, UV Unwrap,
Rigging and Parts start on `REMESH`, `RETEXTURE`, `UV`, `RIG` and `PARTS`; MCP
reports `mesh_policy_source: edit3d_task` and the task. Animate returns a
re-rigged character with clips, so it depends on the captured source: a source
[already skinned to an armature](#replace-an-existing-skin) starts on
[`ANIMATE`](#apply-returned-animation) and keeps its rig, any other mesh starts
on `RIG` and adopts the returned rig and clips, both reported as `edit3d_task`;
the dialog says an unskinned mesh starts on Attach rig. Models in no list and a
model in two lists, such as Rodin Bang after a restart, start on `REMESH`
(`mesh_policy_source: default`), and the dialog says the edit is not from the
job's task. The submitted task is not saved with the job. For other tasks a
skinned source starts on `RIG`, which with `ANIMATE` is the only policy it
accepts; MCP reports `edit3d_task` when the task is Rigging, otherwise
`rigged_source`, and the dialog says the mesh already has a rig. An explicit
choice in the dialog or MCP `mesh_policy` always wins (`requested`), but a
static one on a skinned source, or ANIMATE on an unskinned one, is then
rejected.

**Scene coordinates** (`WORLD`) maps imported positions through the captured
source's inverse world transform. **Object local coordinates** (`LOCAL`) treats
those imported positions as source-local. Neither fits, centers or rescales a
provider result. **Fit and verify** (`FIT`), offered for every policy except
`ANIMATE`, binds both bases as a `FitRequest`: a mirrored or zero-scale source
offers only the object-local base. An explicitly requested placement wins;
otherwise the review starts on `FIT`, except for ANIMATE and for a `REMESH`
that is not the job's own Remesh task, even when requested, whose result need not
be the source surface; those start on scene coordinates (object-local where
required). Choosing a policy in the dialog selects the same default. MCP
`mesh_placement` follows the same order, and explicit `WORLD` or `LOCAL` stay
strict; ANIMATE reports a requested `FIT` as scene coordinates, which it does
not use. Singular or orientation-reversing mappings are rejected. The review
binds the chosen mapping, policy and original-copy choice. For mirrored or
zero-scale sources, the native dialog starts with object-local coordinates and
explains that requirement. It still requires confirmation; explicit MCP `WORLD`
requests remain rejected rather than changing their mapping. For captured-source
review, the default and explanation use the retained captured target's
transform, independently of whichever object is currently selected. Editing
options replaces that approval handle without recapturing the target; changed
source or scene context requires cancellation and fresh review.

Confirmation consumes the handle and verifies saved files on the existing worker.
Main-thread application revalidates the captured source and calls the shared
session command above. Completed jobs persist separate `mesh_edit` local claims,
distinct from `model` imports even after restart. Existing claims keep their
recorded purpose; older `model` entries are not reclassified. Status exposes
the latest session-local `mesh_edit` target, original-copy name, policy,
verified `result_to_source` mapping, `fitted_from` base, `fit_residual`,
`parts_from` and `joined_meshes`; deleted objects have null names. A stopped
application's status names the mesh policy's reason. A failed outcome receipt
can be saved without replacing the mesh again. An uncertain scene outcome never
authorizes replay. There is no automatic blend save. Desktop application records
native undo when Blender history is enabled; see
[native history](#native-undo-for-saved-mesh-edits).

The generic action reviews a destination selected now. The captured-source action
below uses the original exported object. Neither establishes provider alignment,
provider retexture/rig contracts, semantic parts classification or end-to-end
Edit 3D acceptance.


## Applying to the captured mesh source

**Apply to captured source (N)** (with the format for a primary that is not a
GLB), or **Apply alternate to captured source: OBJ (N)** for an alternate, and
MCP `prepare_result_application` with `purpose: mesh_source` use the original
objects exported for the generation's single captured 3D input. Current
selection is ignored. The confirmation still names the targets, selected result,
edit policy, coordinates and Keep original choice before any mutation. More than
one input binding is ambiguous and cannot select an original target
automatically.

Export, static or [skinned](#replace-an-existing-skin), retains a live
`MeshTarget` for each exported object before exporting, rechecks them afterwards
and keys them by the exact upload origin and export metadata. Several objects
are retained together only when every one can be captured and their meshes
total at most 2,000,000 components; larger uploads are never fingerprinted for
this guard. One skinned object over that bound is retained for ANIMATE alone. The
action appears only while the guard is retained. Shared quotes
persist that upload binding in the generation intent. Review resolves only this
retained guard, never an object name or a reconstructed match from disk. Retention
compares the stored export digest with a fresh export fingerprint of the live
mesh. The stricter edit fingerprint has a different format and remains part of
the retained target's validation, rather than substituting for that digest.
Geometry, data identity, names, transforms, parenting and collection membership
must still match. Unrelated scene changes can advance the scene revision without
changing the source; review captures a fresh destination revision, which the
existing application path rechecks after asynchronous file verification.

Undo/redo, file loading, session retirement and restart discard live source
ownership. Stored provenance remains useful history, but cannot restore that
ownership. **Apply mesh edit** remains available for a freshly reviewed explicit
destination, including after restart. A successful remesh changes the original
snapshot, so another original-source application requires a new capture; it is
not silently authorized by the completed job's reuse controls.

Other modifiers, constraints, animation data and other unsupported source
policies remain uploadable where export supports them, without in-place source
ownership. Each session retains at most 128 distinct eligible snapshots without
evicting older ones. Further captures remain upload references but have no
original-source guard. This is explicit local application; it makes no service
request, cannot establish provider alignment, and adds no persistent restoration
command.

### Several captured objects

An Edit 3D upload of several selected meshes (up to 64) is one GLB with one node
per object. When every object was retained and the job's task starts on a policy
listed below, **Apply to N captured sources (M)** (with the format for a primary
that is not a GLB, such as **Apply to N captured sources: FBX (M)**, or **Apply
alternate to N captured sources: OBJ (M)** for an alternate) and MCP
`purpose: mesh_source` apply its result to all of them at once, one to one, or
to none. **Apply mesh edit** still reviews only the active mesh.

- Only `UV`, `RETEXTURE` and `RIG`, which keep each object's geometry, are
  accepted. `REMESH`, `PARTS` and `ANIMATE` are refused before import: one
  returned mesh, part set or clip set cannot be split back onto several objects.
  A job whose Edit 3D task gives no policy starts on `UV` instead of `REMESH`; a
  Remesh or Parts task, or an Animate job on rigged objects, is refused with
  that reason.
- Every result mesh together must be the [same surface](#surface-matching) as
  all the objects together, placed in the scene. Results may come back as one
  merged mesh or one mesh per object, in any order, in any format a mesh edit
  accepts (GLB, glTF, FBX or OBJ). **Scene coordinates** use the
  identity mapping; **Fit and verify** fits only that scene base. **Object local
  coordinates** have no meaning for several objects and are refused.
- `RETEXTURE` gives each object only the result materials its own faces use, in
  first-use order.
- `RIG` gives every object its own weights, with only the bone groups it uses,
  and an Armature modifier to the same returned rig. That rig group is placed in
  scene coordinates, without a parent, in the first object's collections. Rigged
  objects have their skins replaced as [for one object](#replace-an-existing-skin).
- Every object is revalidated immediately before mutation: one deleted, renamed,
  moved or edited object refuses the whole application. All objects are staged
  before any is published; a failed publication or binding restores the objects
  already changed only once every one is proven restorable, and otherwise
  restores none and reports the outcome uncertain. Keep original makes one
  hidden copy per object. One pair of native undo checkpoints covers the
  whole application, and receipt-only recovery never applies it again.

The approval's `target` is null and `targets` lists every object; after
application, `mesh_edit.targets` and `mesh_edit.originals` list them in capture
order. Undo/redo, file loading, session retirement and restart discard this
authority as for one object.


## Retexture without geometry replacement

Choose **Replace textures** in either mesh approval dialog, or pass
`mesh_policy: RETEXTURE` with MCP `purpose: mesh_edit` or `mesh_source`. The
same captured destination, coordinate mapping, Keep original and durable
application controls apply. No generation or service request is made.

Retexture copies the source mesh, preserving its vertex positions, indexed
topology, non-UV attributes, edge flags and shading flags. It replaces **all**
UV layers with the result's names, coordinates and active/render/clone roles,
and adopts the result's material slots and polygon assignments. UV names are
preserved so imported shader references keep their intended map. Old materials
and their node graphs remain untouched; shared source meshes and a requested
original copy retain the previous appearance. Embedded result images stay packed.

The result must be the [same surface](#surface-matching) as the source, as for
UV replacement; split result meshes are matched together. Changed geometry, a UV
seam or a material change inside one source face are rejected instead of
guessed. Result materials and UVs must be nonempty on every result mesh, which
must share the same UV layer names; face material indices must be valid, and
result UV names must not collide with retained source attributes. A result with
color attributes but no UV layers is rejected. A failure restores the exact
source and retains downloaded bytes for a separately reviewed local retry.

The primitive's guarded rollback and the saved command's receipt-only recovery
remain unchanged. Keep original is the user-visible retained copy; native undo
follows the saved-command history contract below. Rig/animation sources and paid
acceptance remain outside this policy;
[several captured objects](#several-captured-objects) are retextured together.
Explicit remesh remains a separate reviewed choice when geometry replacement is
intended.

### Keep the source's texture on chosen faces

A retexture model repaints the whole surface, and a character's face drifts with
it. Replace textures can paint the source's own maps back on some faces after the
result lands: **Keep texture** in the native review, `keep_texture` over MCP.

- `SELECTED`: the faces selected in Edit Mode, read from the captured mesh in
  Object Mode. Selecting every face, as an import does, is no selection.
- `HEAD`: a character's head, found from the shape alone
  (`core/scene/kept_texture.py`). Positions are welded so a mesh split at UV seams
  is one surface again, and connected pieces are told apart: the piece that holds
  the top and reaches lowest is the body. Its horizontal sections, read down from
  the widest one in the top quarter, narrow to a neck and open again at the
  shoulders or a collar within 30% of the height; the neck must be at most 0.85
  of the head's widest section. Other pieces mostly above the neck, such as hair,
  are kept whole and pieces mostly below it, such as a jacket and its collar, are
  not. The body piece is kept whole when it is a head-and-neck shell, and is
  otherwise cut at the neck with a band of 2% of the height. A mesh with no such
  neck keeps nothing, and the review says so.
- `NONE`: the result's texture everywhere.

The review starts on `SELECTED` when some but not all faces are selected, else on
`HEAD` when the captured sources stand like a character (0.5 to 3 m tall at the
scene's unit scale and taller than their widest horizontal extent) and the Edit 3D
form's **Keep the head's texture** is on, else on `NONE`, so a prop or a building
never starts on `HEAD`; chosen explicitly, `HEAD` still needs a neck. The review's
note names the kept faces, and the region is bound to the approval like the policy
and coordinates: changing it reviews again.

After the result's UVs and materials replace the source's, and before the edit is
accepted, each new result image used by a kept face is painted: every texel under
a kept face takes the source's map at the same surface point, sampled through the
source's UVs (bilinear, repeating), and blended by a per-vertex weight interpolated
across each face: 1 on kept faces, falling to 0 over 1% of the bounding-box
diagonal along the surface around a selection, or over 2% of the height across a
neck cut. Empty texels within 8 texels per
2048 of a painted one take its colour, so mipmaps and filtering show no seam.
Maps pair by their role in each material's Principled BSDF: base colour (same
colour space only), tangent-space normal (only where the result keeps the source's
UV layout, since the tangent frame follows it), and roughness and metallic, read
from a Separate Color channel as glTF packs them or directly as a grey value. Only
images this application created change; they are repacked losslessly as PNG, or
OpenEXR for float images. Source materials and images are never written.
`job_status` `mesh_edit.kept_texture` reports `mode`, `source` (`selection`,
`head` or null), `faces`, the `maps` painted and the roles `skipped` with a reason.
A failure rolls the whole application back.

Results on the source's own UV layout, such as Meshy 7 Retexture with
`enableOriginalUv`, which the Edit 3D form turns on, give every map back,
normals included. A face whose result UVs overlap a repainted face's shares its
texels, and the last one painted wins; a texture repeated outside 0 to 1 is
painted at the wrapped texel.


## Native undo for saved mesh edits

The shared saved-mesh command records Blender history immediately before import
and after successful replacement, staging cleanup and rollback-handle finalization.
This covers REMESH, UV, RETEXTURE, PARTS, RIG and ANIMATE from both native
review and local MCP, and [several captured objects](#several-captured-objects)
under one pair of checkpoints. The pre-state includes the latest user edits;
neither checkpoint contains temporary import scenes or private rollback holders.
Undo restores the source data and removes any Keep original copy; Redo restores
the applied data and that copy. After a RIG edit of a skinned source, Undo also
restores its previous skin; after ANIMATE it restores the rig's previous
animation and removes the copied clips.

Automatic checkpoints require a desktop window, Global Undo enabled and at least
two undo steps. The extension does not change preferences. Blender's history size
and memory limits still apply, so Keep original and saving the blend file remain
useful. Background application does not create desktop history; it still marks
the file modified, so Blender asks to save it. A failed initial
checkpoint stops before import or source mutation. If the final checkpoint fails,
the completed edit stays applied, a sanitized warning is logged, and
`mesh_edit.undo_available` is false. It never becomes permission to repeat the edit.
A true value reports that the checkpoint was recorded, not indefinite retention.
If import/application fails after the pre-checkpoint, verified rollback restores
the scene but leaves that checkpoint in history. It can truncate prior redo
history. The command never calls Undo to remove it: doing so can discard the
user's latest edits and invalidate unrelated live targets. A later explicit Undo
still follows the ordinary history-invalidation rules.

Undo/Redo changes Blender scene data only. Durable jobs, local application claims,
download receipts and spending records remain unchanged; Redo does not submit,
download or run application again. Existing history handlers discard live origin
and captured-source ownership. The transient `mesh_edit` status is cleared
before touching potentially retired RNA references and is not rebound by name
after Redo. Pending approvals cannot survive history changes; reuse requires a
fresh explicit destination review. Saving/reopening a blend file does not
restore undo history or source authority from stored names. See
[undo interaction](ui/saved-3d.md#saved-mesh-undo-interaction).

## Apply static parts

The saved-result command's `PARTS` policy preserves the captured source object as
an empty mesh parent and parents one new mesh per imported mesh directly to the
source, with identity local transforms. Child names combine the source name, a
numbered Part prefix and the imported name, subject to Blender's name limits.
Source name, transforms, parenting, collections and existing children remain
unchanged. The prior selection remains active. The parts come from one of two
places, reported as `parts_from`:

- `source_faces`: when the imported meshes together are the
  [same surface](#surface-matching) as the source under the selected or fitted
  mapping, the source mesh itself is split along their boundaries. Segmentation
  providers return the uploaded faces, triangulated, normalized and with UVs and
  materials stripped; each part instead keeps the source's own positions in
  source-local coordinates, UV layers, material slots and face assignments,
  attributes, seams, sharp edges and smooth flags. A smooth-shaded or
  custom-normal source's corner normals are set on each part as custom normals,
  since a part boundary changes the corner fans Blender computes them over, so
  shading across part boundaries is unchanged. A provider that also retextures
  returns parts with their own UVs and materials: when every part carries them,
  the parts adopt them through the verified correspondence as
  [RETEXTURE](#surface-matching) does, UV layers with their names and roles and
  materials per face, each part keeping only the materials its faces use. All
  result faces on one source face must come from one part, the source must have
  no loose vertices or edges, and either every part or none must carry UVs or
  materials; otherwise the result meshes are copied under the verified mapping,
  and the reason, such as **the result splits 4 source faces between parts**, is
  logged.
- `result_meshes`: otherwise, such as for remeshed parts, independent copies of
  the imported meshes are staged with their node transforms baked through the
  explicit mapping or a verified
  [bounds fit](#bounds-fit-for-remeshes-and-copied-parts). Material slots, UVs
  and packed image dependencies stay with the copies.

Which applies is known only after import, so the review describes both.
The policy deliberately treats **every mesh in the selected result as a part**.
Choose the actual segmented artifact, not a variant collection, exploded view or
helper/bounds artifact. The command cannot infer those provider semantics. It
rejects rigs, animation, external dependencies, empty parts, fewer than two or
more than 128 meshes, unsupported attributes and aggregate geometry/attribute
components above the existing synchronous limit. The source must have surface
geometry; an empty parts anchor cannot receive another parts group. Select a
child or the retained original for further mesh operations.

Keep original retains a hidden copy of the previous source geometry. The
shared guarded replacement swaps in empty geometry only after all parts pass
validation; part publication and imported-data cleanup stay inside the same
rollback boundary. A verified failure restores the captured source and removes
new datablocks. Uncertain rollback retains possible applied data and never
permits blind replay. Native Undo/Redo restores the source or the complete parts
group without changing durable job state or issuing service requests.

Known mesh validation or application failures pause delivery with a message to
inspect the saved result, source and edit policy. Uncertain outcomes keep their
receipt-recovery warning and never authorize another application automatically.
See [parts interaction](ui/saved-3d.md#parts-application-interaction). Semantic
part classification remains separate work.


## Attach a returned rig

The explicit `RIG` policy attaches a saved result's skin to one captured source,
unrigged or [already skinned](#replace-an-existing-skin), or to
[several captured objects](#several-captured-objects) at once. It requires one
armature, optional Empty parents and skinned meshes that together are the
[same surface](#surface-matching) at rest under the selected or fitted mapping,
and normalized bone weights for every vertex. Bone group names must match the
rig and the rig may contain at most 1,024 bones; at most 2,000,000 weight
entries are inspected. The usual file and mesh component bounds still apply.
This is a compatible skin transfer by verified vertex correspondence, not
existing-rig retargeting.

The source receives a private copy of its own mesh with the returned weights,
plus one Armature modifier. Geometry, UVs, materials and other supported mesh
attributes remain from the source. Object identity, name, transforms, parenting,
collections and selection remain intact. The returned armature and parent
hierarchy, including their clips, are retained under a new named rig group in
the same collections. That group shares the source's existing parent and uses
`source_world @ result_to_source`, with the verified fitted mapping when one was
used; imported node transforms remain below it.
Move the source and new rig group together afterward. The rig is not parented
to the deformed source, avoiding a dependency cycle. Timeline settings stay
unchanged and clip conversion follows the destination FPS described above.

Morph targets, animation on the returned mesh or its independent animated
parents, extra mesh modifiers, envelope/partial-modifier weights, rig/pose
constraints, drivers and armature-data animation are rejected before source
mutation. Source materials are deliberately retained; RIG does not adopt
returned textures.
Invalid results remain downloaded for inspection or a separate new-group import.

[`rig_application.py`](../scenario/blender/rig_application.py) stages weights on
a private source-mesh copy, then uses the existing mesh replacement/Keep
original boundary. A synchronous internal receipt checks the owned modifier and
weights before rollback. The saved-result command verifies source restoration
and exact new-data cleanup before reporting a known failure; uncertainty never
authorizes another attachment. Native undo/redo restores the rig, weights and
retained original together. Receipt-only recovery records success without
attaching again. UI **Attach rig** and MCP `mesh_policy: RIG` use the same
captured target and optional original-export target guards. Session status
exposes `mesh_edit.rig`; history invalidation retires that status before
dereferencing stale Blender data.
[Apply returned animation](#apply-returned-animation) copies clips onto a
matching existing rig, or retargets a humanoid clip onto it.

### Replace an existing skin

A source already skinned to an armature can be re-rigged in place. Capture
accepts exactly one Armature modifier that deforms through vertex groups, with
no envelopes, vertex-group mask or multi-modifier, bound to a local armature in
the same scene that is not in Edit Mode. The source may be Object-parented to
any armature. Armature-deform (`ARMATURE`) and bone parenting, other modifiers,
shape keys, constraints, mesh/object animation, linked or overridden data and
the other primitive checks still fail closed. Vertex groups without that
modifier are rejected.

The captured target adds the modifier's settings, vertex group names and lock
flags, a digest of every vertex's weights, and the armature's identity, names,
bone names, parents, rest matrices, lengths and deform flags and its world
matrix. Weight entries and bones share the 2,000,000-component work cap; over it,
or on a mesh over it, the weights are not captured and only ANIMATE applies. Any
change makes the target stale before import. Posing or animating the bones does
not: the glTF export excludes Armature modifiers when it applies modifiers, so
the provider receives the unposed source mesh data without the old skin, and
returned geometry is compared with that mesh data, never the evaluated pose.

Application replaces the skin only. The source keeps its identity, name,
transforms, parenting, collections, materials, UVs and geometry. Its old
vertex groups and Armature modifier are removed; the returned weights and one
**Scenario Rig** modifier bound to the retained returned armature take their
place, under the same new rig group described above. When the source is a child
of its old rig, it stays one, and so does the new rig group; the old rig then
moves both without deforming the source. The old armature object and its data
are never modified or removed.

Keep original retains a copy that keeps the old mesh, vertex groups, Armature
modifier and parent, so it still deforms with the old rig. Without it, rollback
recreates the old modifier with every writable setting it had and restores the
old mesh with its groups and weights; Blender assigns the recreated modifier a
new internal identifier and makes it active. Static policies applied to a
skinned target are rejected with an instruction to choose RIG or ANIMATE, before any import or
claim. Without a requested policy, both the native review and MCP start a
skinned source on RIG, or on ANIMATE for an Animate job (see
[the approval defaults](#saved-mesh-edit-approval)); an explicit static policy
is rejected. The resulting skin can be replaced again.
[ANIMATE](#apply-returned-animation) applies returned clips to the existing rig
instead.

## Apply returned animation

The explicit `ANIMATE` policy applies the clips of an Edit 3D **Animate** result
to the rig of a source [skinned to an armature](#replace-an-existing-skin).
Animate providers return a complete re-rigged character: one armature with its
clips, usually with a skinned mesh. Text-to-motion providers return a clip on
their own humanoid skeleton instead, which is
[retargeted](#retarget-a-humanoid-clip). ANIMATE keeps the user's mesh, skin,
armature and object context, copies only the clips onto the armature that the
source's Armature modifier uses, and adds none of the returned objects. Every
mesh that armature deforms follows the clips. An unskinned source is rejected
before import with an instruction to choose RIG, which attaches the returned rig
and keeps its clips.

[`animation_application.py`](../scenario/blender/animation_application.py)
validates the staged import before any change. The result must contain exactly
one armature with at least one clip, plus optional meshes and Empties. Clips are
the armature's active action and its NLA strips' actions, in that order. Each
clip may key only pose-bone location, rotation and scale in the armature's own
action slot, without F-Curve modifiers, and the location, rotation and scale of
the armature object itself. Other animated objects, shape-key or armature-data
animation and other channels are rejected rather than dropped. Keys on the
armature object come from files whose skin leaves the scene root out of its
joints, such as Uthana Text to Motion with its mannequin mesh: the root becomes
the armature object and carries the walk. No bone can take that motion by name,
so such clips are always [retargeted](#retarget-a-humanoid-clip), and refused
for a rig that is not a humanoid.
Every bone a clip animates must exist in the destination rig by name, with the
same parent name, connection, rotation/scale inheritance and local location
setting; rotated bones must use the same rotation mode. They must have no
constraints, and no drivers on their location, rotation or scale, which would
override the clips. Neither armature object may be mirrored, and the
destination may not solo an NLA track, which keeps the clip from playing. When
names, hierarchy, rotation mode or rest pose do not match, the clips are
[retargeted](#retarget-a-humanoid-clip) if both rigs are humanoid skeletons, and
rejected with the first mismatch otherwise, followed by "Rig the mesh again with
Edit 3D > Rigging, then apply the animation again". A refused clip leaves the
rig as it was, and the job row says so: **Animation not applied; the rig is
unchanged**, then the reason.

Both rigs bind the same character in the same rest pose, but a re-rig can orient
a bone differently on it, and keys pose each bone relative to its own rest. Each
animated bone's rest orientation relative to its parent must therefore be within
15 degrees of the destination's, as must, in armature space, that of each
animated bone whose parent is not animated, which carries any unkeyed ancestor's
difference. If it is not, world space is tried instead of armature space, as
when an FBX import turns its armature object and its bones back. Armature space
comes first, so a character turned in the scene plays the clip in its own
facing. One provider re-rigging its own rigged character moved some joint rest
orientations by up to about 11 degrees, while a skeleton built in another pose
or orientation differs by tens of degrees, which no correction makes right.

Within that limit, copied keys are corrected so that each bone moves the mesh
as the returned clip moves the returned character. With C the rotation from the
destination bone's rest orientation to the result's, in the space chosen, each
quaternion key q becomes C q C⁻¹ and each location vector l becomes C l, in
every key and handle; automatic Bezier handles become free. The destination's
rest heads stay, so the mesh bends about its own joints. A corrected bone must
key the components of each location and quaternion channel together, with
constant, linear or Bezier interpolation, scale uniformly to within 0.01% and
use quaternion rotation, as glTF clips do; otherwise the result is rejected.

An FBX result gets the same checks: Blender's FBX importer restores the rest
orientation of a rig Blender exported, while an FBX rig built with other bone
axes than the destination fails with "The destination rig's rest pose does not
match"; bones are never re-oriented to fit. The importer also connects every
bone whose head sits on its parent's tail, so an FBX's clips fit a rig attached
from the same kind of file, while an unconnected destination rig with those
bones fails with "Animated bones must keep the same hierarchy".

Location keys are armature-space distances. When any location key leaves its
bone's rest head, every location key and handle is scaled by the ratio of the
destination's summed parent-relative bone head offsets to the result's, over
bones whose names and parent names match. A returned rig with 0.01 object scale
and centimetre bones therefore lands in a metre rig's units; the result's object
scale is not used. A ratio that cannot be derived is rejected. Rest-head
location keys, as sampled exports write for every bone, stay unchanged. The
coordinate mapping and Keep original choice are not used: ANIMATE changes no
mesh data.

Application copies each clip as a new action named after the destination rig and
the clip, keeps only its armature slot, renamed after the rig, and rescales and
corrects it.
The first clip becomes the rig's active action. The previous active action, if
any, moves to a muted NLA track with its slot, and each copied clip gets its own
muted NLA track, as Blender's importer does, so changing the active action loses
none of them. The active action blends as Replace at full influence; existing
NLA tracks and the extrapolation stay as they were. GLB and glTF clip timing
follows the destination's effective frame rate through the
[shared staging scene](#rigged-and-animated-model-import); FBX clips keep the
file's. A scene frame range still at Blender's default, 1 to 250 without a
preview range, becomes the first clip's, rounded out to whole frames (ends
within 0.001 of a frame count as on it), so the clip plays in full; a range the
user set stays. The current frame and frame rate stay unchanged, and rollback
restores the range.

The captured target guards the rig's identity, bones, rest and transform, so a
changed rig is stale before import; posing or animating it is not. Animation
assigned to the rig after review is kept the same way. The rig must not be in
NLA tweak mode. A failure after assignment restores the rig's previous action,
slot and tracks exactly before the shared command removes the new clips and
verifies the datablock sets. An unexpected difference remains uncertain and
never authorizes another application. Native undo and receipt-only recovery
follow the [saved mesh history](#native-undo-for-saved-mesh-edits). Session
status reports the rig in `mesh_edit.rig`, the new clip names in
`mesh_edit.clips` and the largest rest correction applied to an animated bone,
in degrees rounded to 0.1, in `mesh_edit.rest_correction_deg` (null for other
policies and for retargeted clips). A nonzero correction also shows **Clips
adjusted to this rig's rest pose by up to N°** in the job row until undo history
changes. `mesh_edit.frame_range` gives the frame range the first clip set, or
null when the scene kept its own. UI **Apply animation** and MCP
`mesh_policy: ANIMATE` use the same captured target guards.

### Retarget a humanoid clip

Text-to-motion models such as Uthana and Viggle animate their own skeleton, an
Unreal or Mixamo one, and Meshy's text-to-motion an SMPL one. When bones do not
match by name, [`motion_retarget.py`](../scenario/blender/motion_retarget.py)
retargets the clips if both rigs are recognized humanoids:
[`humanoid.py`](../scenario/core/scene/humanoid.py) names 22 body slots (hips,
four spine and neck bones, head, shoulders, arms, forearms, hands, thighs, shins,
feet and toes) for the Meshy, Mixamo, SMPL and Unreal bone conventions, after
any `namespace:` prefix. Every slot bone must exist and descend from its parent
slot's bone; two bones with the same name under different prefixes make a rig
unrecognized. Other skeletons keep the name-matching error.

Each slot bone takes the returned bone's world orientation, frame by frame,
whatever the bone axes or rest pose. The two rest skeletons are aligned through
a character frame built from their rest heads (up from the hips to the head,
left from the right thigh to the left one), and each destination bone turns by
the swing that takes its rest direction, head to child slot head, onto the
returned one, so a T-pose clip plays on an A-pose rig. Hands, the head and toes
follow their parent slot's swing. Feet only turn on the floor to meet the
returned ones at rest, since both rests stand flat, so each foot keeps its own
pitch however high its ankle sits, then follows the returned foot's turns. The
clip's first frame gives the returned character's facing on the floor:
orientations and root motion go through level character frames, so the
character moves in its own facing wherever it stands. The hips move by the
returned hips' travel since that first frame, scaled by the ratio of the two
rigs' mean thigh plus shin lengths. One height for the whole clip then puts the
feet on the rest floor, whether the clip starts with soft knees or raised heels:
the median over frames of how far the lowest ankle or ball joint stands over its
rest height on the rig, against how far it stands over its lowest height in the
clip on the returned skeleton, scaled like the travel. When the clip also keys
the returned armature object, its world transform is evaluated from those keys
every frame, so its travel and turns reach the hips the same way; the destination
rig object itself is never keyed.

Every frame of the clip is sampled and keyed linearly into a new action: hips
location and rotation, and every other slot's rotation in its bone's rotation
mode, quaternion with sign continuity or Euler. Bones outside the slots, such as
fingers, twist and face bones, keep their current pose, as does an extra rig
bone between two slot bones. Slot bones and their ancestors
must inherit rotation and scale with local location, on both rigs; slot bones
may not use axis-angle rotation and, as above, may carry no constraints or
drivers. Keys are not rest-corrected, so `mesh_edit.rest_correction_deg` is null
and `mesh_edit.retargeted_from` names the returned skeleton (Meshy, Mixamo, SMPL
or Unreal); the job row shows **Clips retargeted from a Mixamo skeleton**, for
example. A rig whose own rest pose is wrong for its mesh, such as a forearm bone
pointing away from the forearm, plays the clip wrong there too.
