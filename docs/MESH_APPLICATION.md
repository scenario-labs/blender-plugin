# Explicit mesh application

`scenario.blender.mesh_application.apply_mesh` is a synchronous Blender main-thread
primitive for applying one already imported mesh to one explicit source object.
It has no network, import, job, UI or MCP side effects and never reads selection to
choose a target. Existing prototype import behavior is unchanged.

```python
receipt = apply_mesh(
    captured_scene,
    captured_source,
    imported_primary_mesh,
    policy="REMESH",                 # or "UV"
    result_to_source=local_mapping,  # explicit finite, orientation-preserving affine 4x4 matrix
    keep_original=True,
)
# The caller owns the receipt until one of these explicit decisions:
receipt.accept()                    # retain the application
# receipt.rollback()                # restore if both meshes are still unchanged
```

The caller must validate its captured file/scene/object revision immediately before
this call. It must also select the primary imported mesh and establish the mapping
from result mesh coordinates into source-local coordinates. Reflection and singular
mappings are rejected; this slice does not define a handedness/normal-flip policy. The primitive does not
infer that mapping from object placement, names or current selection. It does not
prove cloud provenance, safe download/import, or that a late result still matches
its original inputs. The verified saved-mesh command below adds receipt-bound
import and shared-session bookkeeping; UI/MCP approval and operation-bound input
metadata remain integration work under #65 and #99.

## Supported policies

| Policy | Geometry and attributes | UVs | Materials |
| --- | --- | --- | --- |
| `REMESH` | Copy result mesh and bake the explicit local mapping | Adopt result UV layers | Adopt result mesh material slots and polygon assignments |
| `UV` | Copy source mesh; require exactly matching indexed vertices, edges, polygons and loops, with exact positions after mapping | Copy coordinates from exactly one result UV layer to the source's active layer; preserve its name and other layers; create a layer if absent | Preserve source slots and polygon assignments |

A remesh deliberately replaces all source mesh attributes with the result's data.
UV matching is exact, with no epsilon or nearest-point guess; different indexing,
seam-split vertices or rounded coordinates fail closed. Materials themselves remain
shared datablocks: their node graphs/images are never copied, mutated or reverted.
The source object's identity, name, local/world transforms, parenting, collection
membership, selection and object custom properties remain intact. Shared source
and imported-result mesh datablocks are never edited in place.

The source's active material index may be clamped by Blender when a remesh has
fewer slots. Rollback restores the original index only if the applied index is
unchanged; a later user change requires explicit review.

Only local, non-overridden meshes in Object Mode are supported. Modifiers,
constraints, vertex groups, shape keys, animation, armature/bone/vertex parenting,
vertex-parented children, object material overrides and custom mesh properties are
rejected. Generic attributes are limited to boolean, scalar float/integer, integer
2D, float 2D/3D and float/byte color types. Other types fail closed. Rigging,
retexture, segmentation grouping, animation transfer and multi-object replacement
need separate policies. Supplying one explicit result object does not classify
other returned helper objects, maps or alternate meshes.

## Transaction and ownership

Staging copies and validates the candidate before swapping only `source.data`.
An exception during staging or publication restores the original pointer/material
index and removes only newly created staging objects/meshes. The original source,
imported result and downloaded files remain available for a local retry without
rerunning generation.

With **Keep original**, a duplicate object using the original mesh is linked into
the source's collections with the same parenting/transforms. It becomes user-owned
once returned, remains accessible as `receipt.original`, and survives both accept
and rollback. It shares the old mesh with any existing users; subsequent edits to
that old mesh prevent automatic rollback.

Without Keep original, a private unlinked object retains the original mesh until
the caller finalizes the receipt. `accept()` releases that holder and removes the
original mesh only if it has no remaining users and is unchanged. Shared meshes,
fake-user ownership, renamed meshes, new metadata and other edits are retained.
`rollback()` restores the original mesh and then releases the holder. A linked,
renamed, configured or otherwise adopted holder is retained for user review. There is no destructor that
accesses Blender. Callers must finalize their receipts; this is an in-memory
transaction boundary, not persisted recovery or integration with Blender's global
undo stack. File loading, undo that removes datablocks and source deletion can make
a receipt unusable; it never re-finds targets by name.

Rollback rechecks the supported object structure as well as source/scene membership,
the applied mesh pointer, active material selection and fingerprints of both original
and applied meshes. Adding modifiers, constraints, vertex groups, shape keys,
animation, incompatible parenting, object material overrides or mesh custom properties
requires explicit review before rollback. These guards protect topology-dependent
data and metadata outside the fingerprint. A refusal leaves the receipt open;
removing the added structure allows retry if the remaining guards still pass.
The fingerprints cover geometry, supported generic attributes, UV layer roles and material slot
bindings, so editing the applied mesh in place cannot silently lose user work.
Shader node graph edits are outside that fingerprint and are never reverted.
Rollback removes its unchanged staged mesh only when no other user owns it; it
never removes the imported result or a mesh adopted by another object.

Fingerprinting is linear and runs on the main thread. A limit of 2,000,000 combined
vertices, edges, loops, polygons and generic-attribute entries bounds each pass;
this is a work cap, not a latency guarantee. Large meshes and unsupported data
require another application path. Installed-ZIP tests use local synthetic meshes;
no OAuth or paid cloud acceptance is implied.

## Explicit saved static GLB import

The shared saved-job path can import one explicitly selected static
`model/gltf-binary` result into a new **Scenario Model** collection and parent
group. It places the model's world-space bottom center at the approved 3D cursor,
retains the imported hierarchy and materials, packs embedded images, and leaves
existing objects, selection, active object and viewport shading unchanged. It
does not replace an existing source mesh or implement the edit policies above.
Alternate result files and maps remain saved; only the selected GLB is imported.
One import consumes the job's application claim.

[`glb.inspect_glb`](../scenario/core/scene/glb.py) checks the
[GLB 2.0 container](https://github.com/KhronosGroup/glTF/blob/98015344c6a5f5a3a96686cbd77960a8b09f6276/specification/2.0/Specification.adoc)
and the supported import policy before Blender runs. It requires one scene,
one embedded binary buffer and no URI references, animation or skins. Limits
are 256 MiB of file bytes, 8 MiB of JSON, 10,000 nodes and 10 million accessor
entries. This is a bounded policy preflight, not a complete glTF validator or
proof against every expensive decoder input; Blender validates geometry and
textures. JSON glTF, FBX, OBJ, splats, multiple scenes, external files, rigs and
animations need separate integration. Unsupported downloads remain available.

[`model_application.apply_model`](../scenario/blender/model_application.py)
rehashes the exact local receipt, writes a private snapshot and imports into a
disposable scene with scene extras and selection changes disabled. Publication
moves only the new objects into a new destination group. Embedded images remain
packed after temporary files are removed. Failures remove only newly created
data and verify the final datablock sets, including staging scenes and shape keys.
Incomplete scene cleanup remains uncertain instead of authorizing another import;
there is no receipt-only retry when scene success is unknown. Temporary snapshot
cleanup is attempted separately: a filesystem cleanup error reports a sanitized
warning and may leave a temporary file, but preserves a completed packed import.
Copying, hashing and decoding are synchronous on the main thread, so large models
can pause Blender. There is no automatic blend save or global-undo transaction.

Native **Import static model (N)** and MCP `prepare_result_application` with
`asset_id` capture the scene revision and exact cursor. Approval is consumed once;
worker verification and destination revalidation precede the durable claim.
The current scene must be local and in Object Mode both at preparation and after
verification. Rejection before the claim leaves a ready job ready.
A moved cursor, changed scene/file/context or stored revision requires review
again. Completed jobs can import another saved model under a separate local
claim after fresh approval. An interrupted original or local `applying` claim
cannot be replayed.
Receipt-only retry saves known success without importing another model, and
session shutdown releases that retry handle. This remains partial #65/#99 work:
in-place remesh/UV/retexture, rig/animation transfer and edit-specific recovery
are not established by a successful new-object import.

## Captured source and verified saved-mesh command

`mesh_application.capture_target(scene, source)` freezes the live source object,
mesh, names, bounded geometry/attribute fingerprint, transforms, parenting,
collection membership and active material index. It accepts one local scene in
Object Mode and retains the primitive's unsupported-data checks. It does not infer
selection. Capture evaluates the current view layer so pending parent transforms
cannot hide behind a stale world matrix. `validate_target` rejects intervening
edits, replacement, deletion or membership in another scene. Capture the mesh
snapshot first, then the `JobSession` origin, before asynchronous work; a target captured afterward cannot establish the old
input's identity. Restart/file load requires a fresh explicit destination review.

`mesh_result_application.apply_saved_mesh(target, item, path, policy=...,
result_to_source=..., keep_original=...)` connects the existing primitive to one
verified static GLB. It shares the new-object importer's receipt/hash preflight,
private byte snapshot, isolated staging scene and image packing. It requires
exactly one mesh with optional Empty parents; multiple meshes and other object
types fail rather than selecting the first variant. The caller explicitly chooses
`REMESH` or `UV` and Keep original.

The required finite, orientation-preserving mapping converts **Blender-imported
GLB scene coordinates** into **source-local coordinates**. Imported node transforms
are composed into it after Blender's glTF axis conversion. There is no automatic
centering, scale fitting, alignment guess or source-object movement. This local
mapping does not prove a provider preserved the input's coordinates or topology.
UV still requires exact indexed topology/positions after mapping and one UV layer.

The source is revalidated immediately before replacement. Imported staging objects
are removed; replacement material/image dependencies remain packed. Keep original
retains a separate unselected copy, preserving the previous selection and active
object. Without it, the primitive may release the unchanged, unused original mesh.
A returned result is finalized and contains the source, optional original and
policy; it is not a persistent rollback handle or a global undo transaction.

Successful cleanup sweeps unused imported datablocks across the shared importer's
categories, including helper actions, while retaining existing data, live
dependencies and fake-user ownership. Groups are released before their images.
Animated GLBs are rejected by preflight before import. Morph targets can decode,
but the mesh policy rejects their shape keys; removing the imported mesh also
removes its keys. Native tests require exact datablock restoration before a
confirmed failure permits a newly reviewed local attempt.

On failure after replacement, the command attempts guarded rollback before any
new-data cleanup. It permits a known local failure only after both the exact
captured source and original datablock sets are restored. An edited source,
failed rollback or incomplete cleanup remains uncertain; new data is retained
when removing it could destroy a possibly applied result. A temporary-file cleanup
warning does not undo a completed packed result.

`JobSession.apply_recovered_mesh` supplies owner-issued verification, exact
scene/object origin resolution and a durable claim before mutation. Original
ready/confirmed-failed jobs use their recovered claim; completed jobs use a
separate `model` local claim whose destination identifies the source object.
`retry_model_receipt` records only known success, never another replacement.
See [session ownership](BLENDER_JOB_CONTEXT.md#verified-saved-mesh-replacement).

Installed synthetic tests cover remesh and exact-topology UV, parented/scaled
sources, shared originals, packed materials, explicit node-transform mapping,
selection, source changes, multi-scene/multi-mesh rejection, rollback failure,
separate local reuse and persistence-only recovery. Native UI/MCP approval,
operation-bound export metadata, provider coordinate contracts, rig/retexture/
segmentation policy and global undo remain integration work under #65/#99.
There are no new service calls or live/provider acceptance claims in this command.
