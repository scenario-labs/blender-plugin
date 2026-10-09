# Saved material application

The shared saved-job command applies one unambiguous saved texture set to one
explicitly approved mesh material slot. It creates a new Principled BSDF material,
loads exact receipt-bound PNG/EXR snapshots as new packed images, and preserves
existing materials and all other slots. It does not regenerate, download again,
save the blend file or change viewport shading.

## Texture selection and shader behavior

The [stored texture roles](RESULT_TRANSFERS.md#texture-result-semantics) come from
the scoped SDK asset response, independently of file MIME. Application requires
an albedo or base map, no repeated role, and at most one of roughness and smoothness.
When both albedo and base are present, the dedicated albedo map supplies Base Color;
the base preview stays saved without being loaded into the material. Base is the
fallback when no albedo is present. This choice uses stored roles, regardless of
asset order. Application does not select the first variant, infer roles from
filenames or combine multiple texture sets. Unclassified assets remain saved and unused.
Each selected map needs a verified receipt and a supported PNG/EXR media type;
Blender must decode the same bounded bytes and pack the image before assignment.
PNG maps may use 8- or 16-bit grayscale, RGB or RGBA samples. Scalar maps such as
metallic, smoothness and height can therefore retain their grayscale encoding;
no file conversion or regeneration is required. Palette and grayscale-alpha PNGs
remain unsupported. Receipt, CRC, byte, pixel and chunk limits still apply.

UI and MCP offer material application only when the saved metadata passes the
same texture-selection check used by approval. An unsupported JPEG/WebP map,
missing receipt, ambiguous role or excessive combined size hides the action;
the files remain saved. This availability check does not decode images or
verify file bytes. Worker verification and destination checks still run after
explicit approval.

| Map | New material behavior |
| --- | --- |
| Base/albedo | sRGB image into Principled Base Color |
| Roughness | Non-Color image into Roughness |
| Smoothness | Non-Color image inverted into Roughness |
| Metallic | Non-Color image into Metallic |
| Normal | Non-Color image through Blender's tangent-space Normal Map node |
| Height | Non-Color image through Bump, with distance 0.05; no geometric displacement |
| AO/edge | Named packed texture nodes retained for deliberate artist wiring |

All textures use the approved active UV map by name. This wiring does not prove
provider normal-map handedness, channel layout, real-world scale, seamlessness or
color fidelity. There is no automatic alpha, emission or ambient-occlusion blend.
The local operation is bounded to 256 MiB of combined map bytes and 32 million
combined decoded pixels, plus the existing per-image format limits. These bounds
do not guarantee decoder latency; copying, decoding and graph construction run
synchronously on Blender's main thread.

## Destination and recovery

**Apply saved material** and MCP `prepare_result_application(purpose: material)`
capture the current scene, active mesh identity, data pointer, active slot,
slot bindings, face-to-slot indices and active UV name. The target must be local,
non-overridden, in Object Mode, have UVs, and own a single-user mesh. An object
shared between scenes is rejected. At most 128 slots and one million polygons
bound synchronous destination checks. Nothing is chosen again from selection
after confirmation; a late result cannot attach to a different active object.

Both surfaces consume the same approval through `apply_result_application`.
Receipt verification runs on the shared worker. Current scene/target revisions
and slot state are checked again before the durable application claim. A stale
or changed destination leaves the saved job available for fresh review.

The approved scene must still be selected at admission and after verification,
as required by the shared session for image, media, model and World application
too. Switching scenes stops assignment before any durable claim or material
change. Return to the intended scene and approve it again. Changing only the
active object within that scene does not redirect the captured mesh target.

Assignment replaces the approved existing slot, or adds the first slot when none
exists. It leaves geometry, UVs, face indices, transforms, selection, old material
node graphs and unrelated scene data intact. A failure restores slot bindings and
face indices, removes only new material/image data, then checks the outcome.
Only a verified complete rollback permits `apply_failed` and another local
review. Incomplete cleanup keeps the claim uncertain and forbids repeated
assignment. Downloaded files remain available.

If scene assignment succeeds but its receipt write fails, **Save import receipt**
saves that known result without rebuilding or assigning again. Shutdown clears
pending receipt handles. An interrupted `applying` claim without a known successful
handle needs explicit inspection; it cannot be assumed safe to repeat.

This slice has no global undo entry or persistent restoration handle. Old material
datablocks are not edited, but unused data is subject to Blender's normal purge
and save rules. Preserve a desired old material yourself. Completed jobs can
apply saved maps again through a fresh destination approval and separate durable
local claim. Multi-object/shared-mesh policies and texture-set selection remain
separate work. Synthetic native tests do not establish live provider or
full Materials/release acceptance.
