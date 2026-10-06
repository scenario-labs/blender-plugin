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
    policy="REMESH",                 # or "UV" / "RETEXTURE"
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
| `RETEXTURE` | Copy source geometry and non-UV attributes; require exact indexed topology and mapped positions | Replace all layers with result names, coordinates and active/render/clone roles | Adopt nonempty result slots and valid face assignments; preserve existing shader datablocks |
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
segmentation grouping, animation transfer and multi-object replacement
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

## Explicit saved GLB import

The shared saved-job path can import one explicitly selected
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
one embedded binary buffer and no URI references. New-group imports retain skins
and node transform/morph-weight animations. Limits are 256 MiB of file bytes,
8 MiB of JSON, 10,000 nodes, 10 million accessor entries, 128 skins, 128 animation
clips and 10,000 total joints or animation channels. This is a bounded policy
preflight, not a complete glTF validator or proof against every expensive decoder
input; Blender validates geometry and textures. JSON glTF, FBX, OBJ, splats,
multiple scenes, external files and pointer-based animation need separate
integration. Unsupported downloads remain available. In-place mesh policies
keep the default static-only preflight.

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

Native **Import model (N)** and MCP `prepare_result_application` with
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
provider-specific edit contracts, rig/animation transfer and edit-specific recovery
are not established by a successful new-object import.

## Rigged and animated model import

The new-group path keeps imported armatures, bone hierarchy, vertex weights,
shape keys, actions and NLA clips. Blender activates the first clip and retains
other clips in muted NLA tracks. Animation times use the destination scene's
current effective frame rate; time zero maps to frame zero. Import leaves the
current frame/subframe, frame range and frame rate unchanged. It does not shift
clips to the current frame, extend the timeline or retarget animation to an
existing rig. Moving the new parent group moves the imported character together.

Armature construction requires the staging scene to own the active window and
view layer while Blender's importer runs. The importer restores both afterward,
including on failure, and disables generated bone-display helper geometry.
Ordinary background Blender sessions retain an off-screen window and support
that path. An explicitly windowless caller can import static models or apply a
saved static mesh using its scene and view layer; rigged models are rejected
before importer execution when no window is available.
It also restores the optional glTF animation UI list on pre-existing scenes:
that upstream UI writes outside the import context. Imported actions and NLA
tracks remain on their new owners. Supported Blender 5.0/5.1/5.2 importers multiply
seconds by `fps * fps_base`; the disposable scene uses reciprocal `fps_base` so
clips match the destination's effective `fps / fps_base` without changing its
settings. Native coverage includes a fractional frame rate, deformation, multiple
clips, UI-list restoration and complete cleanup after failed publication.

This imports a complete new character. Applying a returned rig or animation to
the original captured mesh remains separate #99 work. Native global Undo is not
added to this new-group command. See [interaction evidence](UI_STYLE.md#animated-model-import-interaction)
for the exact packaged desktop check and its limits.

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
exactly one mesh with optional Empty parents for `REMESH`, `UV` and `RETEXTURE`.
The explicit `PARTS` policy accepts 2 to 128 static surface meshes in that one GLB;
other object types fail. The caller chooses the policy and Keep original.
Multiple result assets are never combined or ranked automatically.

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
policy and whether a desktop undo checkpoint was recorded; it is not a persistent
rollback handle. See [native history](#native-undo-for-saved-mesh-edits).

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
separate `mesh_edit` local claim whose destination identifies the source object.
`retry_model_receipt` records only known success, never another replacement.
See [session ownership](BLENDER_JOB_CONTEXT.md#verified-saved-mesh-replacement).

Installed synthetic tests cover remesh and exact-topology UV, parented/scaled
sources, shared originals, packed materials, explicit node-transform mapping,
selection, source changes, multi-scene/multi-mesh rejection, rollback failure,
separate local reuse and persistence-only recovery. Provider coordinate contracts
and rig/segmentation policy remain integration work under #65/#99.
There are no new service calls or live/provider acceptance claims in this command.

## Saved mesh edit approval

**Apply mesh edit (N)** and MCP `prepare_result_application` with
`purpose: mesh_edit` review one saved static GLB against the currently active
mesh. The review names the scene, source and selected asset. `REMESH` replaces
geometry, UVs and mesh materials; `UV` replaces only active UVs and requires
exact indexed topology and positions. **Keep original** defaults to enabled.

**Scene coordinates** (`WORLD`) maps imported positions through the captured
source's inverse world transform. **Object local coordinates** (`LOCAL`) treats
those imported positions as source-local. Neither fits, centers or rescales a
provider result automatically. Singular or orientation-reversing mappings are
rejected. The review binds the chosen mapping, policy and original-copy choice.
For mirrored or zero-scale sources, the native dialog starts with object-local
coordinates and explains that requirement. It still requires confirmation;
explicit MCP `WORLD` requests remain rejected rather than changing their mapping.
For captured-source review, the default and explanation use the retained captured
target's transform, independently of whichever object is currently selected.
Editing options replaces that approval handle without recapturing the target;
changed source or scene context requires cancellation and fresh review.

Confirmation consumes the handle and verifies saved files on the existing worker.
Main-thread application revalidates the captured source and calls the shared
session command above. Completed jobs persist separate `mesh_edit` local claims,
distinct from `model` imports even after restart. Existing claims keep their
recorded purpose; older `model` entries are not reclassified. Status exposes
the latest session-local `mesh_edit` target, original-copy name and policy;
deleted objects have null names. A failed outcome receipt can be saved without
replacing the mesh again. An uncertain scene outcome never authorizes replay.
There is no automatic blend save. Desktop application records native undo when
Blender history is enabled; see [native history](#native-undo-for-saved-mesh-edits).

The generic action reviews a destination selected now. The captured-source action
below uses the original exported object. Neither establishes provider alignment,
provider retexture contracts, rig/segmentation policy or end-to-end Edit 3D acceptance.


## Applying to the captured mesh source

**Apply to captured source (N)** and MCP `prepare_result_application` with
`purpose: mesh_source` use the original object exported for the generation's
single captured 3D input. Current selection is ignored. The confirmation still
names the target, selected result, remesh/UV policy, coordinates and Keep original
choice before any mutation. More than one input binding or source object is
ambiguous and cannot select an original target automatically.

Single static-mesh export retains a live `MeshTarget` before exporting, rechecks
it afterwards and keys it by the exact upload origin and export metadata. Shared
quotes persist that upload binding in the generation intent. Review resolves only
this retained guard, never an object name or a reconstructed match from disk.
Retention compares the stored export digest with a fresh export fingerprint of
the live mesh. The stricter edit fingerprint has a different format and remains
part of the retained target's validation, rather than substituting for that digest.
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

Modifiers, constraints, rig/animation data and other unsupported source policies
remain uploadable where export supports them, without in-place source ownership.
Each session retains at most 128 distinct eligible snapshots without evicting older
ones. Further captures remain upload references but have no original-source guard.
This is explicit local application; it makes no service request, cannot establish
provider alignment, and adds no persistent restoration command.


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

The mapping must give exactly matching indexed topology and positions, as for
UV replacement. Rounded positions, reordered or seam-split vertices and changed
geometry are rejected instead of guessed. Result materials and UVs must be
nonempty, face material indices must be valid, and result UV names must not
collide with retained source attributes. A failure restores the exact source
and retains downloaded bytes for a separately reviewed local retry.

The primitive's guarded rollback and the saved command's receipt-only recovery
remain unchanged. Keep original is the user-visible retained copy; native undo
follows the saved-command history contract below. Rig/animation sources,
multiple meshes, provider coordinate/topology guarantees and paid acceptance
remain outside this policy. Explicit remesh remains a separate reviewed choice
when geometry replacement is intended.


## Native undo for saved mesh edits

The shared saved-mesh command records Blender history immediately before import
and after successful replacement, staging cleanup and rollback-handle finalization.
This covers REMESH, UV, RETEXTURE and PARTS from both native review and local MCP. The
pre-state includes the latest user edits; neither checkpoint contains temporary
import scenes or private rollback holders. Undo restores the source data and
removes any Keep original copy; Redo restores the applied data and that copy.

Automatic checkpoints require a desktop window, Global Undo enabled and at least
two undo steps. The extension does not change preferences. Blender's history size
and memory limits still apply, so Keep original and saving the blend file remain
useful. Background application does not create desktop history. A failed initial
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
and captured-source ownership. The transient `mesh_edit` status is cleared before touching potentially retired
RNA references and is not rebound by name after Redo. Pending approvals cannot
survive history changes;
reuse requires a fresh explicit destination review. Saving/reopening a blend file
does not restore undo history or source authority from stored names.

Installed native tests exercise actual undo/redo for all three policies, retained
copies, materials, stale approvals and unchanged durable records/request counts.
They force checkpoint eligibility in the background runner while retaining the
real native history operators. Separate desktop proof is recorded in
[UI interaction evidence](UI_STYLE.md#saved-mesh-undo-interaction).

## Apply static parts

The saved-result command's `PARTS` policy preserves the captured source object as
an empty mesh parent. It stages independent copies of every imported mesh, bakes
imported node transforms through the explicit coordinate mapping, then parents
the copies directly to the source with identity local transforms. Child names
combine the source name, a numbered Part prefix and the imported name, subject
to Blender's name limits. Material slots, UVs and packed image dependencies stay
with the copied part meshes. Source name, transforms, parenting, collections and
existing children remain unchanged. The prior selection remains active.

The policy deliberately treats **every mesh in the selected GLB as a part**.
Choose the actual segmented artifact, not a variant collection, exploded view or
helper/bounds artifact. The command cannot infer those provider semantics. It
rejects rigs, animation, external dependencies, empty parts, fewer than two or
more than 128 meshes, unsupported attributes and aggregate geometry/attribute
components above the existing synchronous limit. The source must have surface
geometry; an empty parts anchor cannot receive another parts group. Select a
child or the retained original for further mesh operations.

Keep original retains an unselected copy of the previous source geometry. The
shared guarded replacement swaps in empty geometry only after all parts pass
validation; part publication and imported-data cleanup stay inside the same
rollback boundary. A verified failure restores the captured source and removes
new datablocks. Uncertain rollback retains possible applied data and never
permits blind replay. Native Undo/Redo restores the source or the complete parts
group without changing durable job state or issuing service requests.

Known mesh validation or application failures pause delivery with a message to
inspect the saved GLB, source and edit policy. Uncertain outcomes keep their
receipt-recovery warning and never authorize another application automatically.

The exact packaged ZIP passed 699 installed native tests on each of macOS arm64
Blender 5.0.1, 5.1.2 and 5.2.1. Synthetic cases cover transformed/parented sources,
existing children, shared originals, mapping, count/component limits, empty-anchor
rejection, publication/cleanup failures, uncertain rollback, captured-source
UI/MCP application and native history. See [desktop evidence](UI_STYLE.md#parts-application-interaction).
Provider alignment, semantic part classification, rigs/animation and integrated
release acceptance remain separate work.
