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
its original inputs. Shared job lifecycle delivery and durable APPLIED bookkeeping
remain integration work under #65 and #99.

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
the caller finalizes the receipt. `accept()` releases that holder; `rollback()`
restores the original mesh and then releases it. A linked, renamed, configured or
otherwise adopted holder is retained for user review. There is no destructor that
accesses Blender. Callers must finalize their receipts; this is an in-memory
transaction boundary, not persisted recovery or integration with Blender's global
undo stack. File loading, undo that removes datablocks and source deletion can make
a receipt unusable; it never re-finds targets by name.

Rollback checks source/scene membership, the applied mesh pointer, active material
selection and fingerprints of both original and applied meshes. The fingerprints
cover geometry, supported generic attributes, UV layer roles and material slot
bindings, so editing the applied mesh in place cannot silently lose user work.
Shader node graph edits are outside that fingerprint and are never reverted.
Rollback removes its unchanged staged mesh only when no other user owns it; it
never removes the imported result or a mesh adopted by another object.

Fingerprinting is linear and runs on the main thread. A limit of 2,000,000 combined
vertices, edges, loops, polygons and generic-attribute entries bounds each pass;
this is a work cap, not a latency guarantee. Large meshes and unsupported data
require another application path. Installed-ZIP tests use local synthetic meshes;
no OAuth or paid cloud acceptance is implied.
