# Blender boundaries

Read [AGENTS.md](../../AGENTS.md), [UI style](../UI_STYLE.md) and
[validation](../development/validation.md) before changing Blender-facing code.
These requirements apply to `scenario/blender/`, scene tools in `scenario/mcp/`
and native tests. Pure protocol and core modules must remain free of `bpy`.

## Threads, context and storage

Keep `bpy` access on Blender's main thread. The current
[pump](../../scenario/blender/pump.py) drains prototype events in the GUI;
[MCP service](../../scenario/blender/mcp_service.py) supplies headless queue
processing. A GUI timer is not proof that background mode delivers work.
Never mutate properties in `draw()` or keep a worker dependent on a live panel.

Check `bpy.app.online_access` before network activity. Store state and cache
through `bpy.utils.extension_path_user`; never write into the installed package.
Use an isolated disposable profile for every development build or probe.

New shared-runtime integration must use explicit account, project, scene and
target identity. [JobSession](../BLENDER_JOB_CONTEXT.md) captures and validates
origins; names alone cannot identify a deleted or replaced object. Closing a
view must not cancel application-owned jobs or route their results elsewhere.

## Scene application

[Mesh application](../MESH_APPLICATION.md) supports explicit reversible remesh
and UV policies with guarded rollback. It is a synchronous primitive, not the
complete edit-3D generation flow. Preserve materials, object context and the
documented ownership checks; do not relax rollback checks merely to make an
edited target pass.

[World application](../WORLD_APPLICATION.md) preflights supported image formats,
loads and packs the image, and installs a new World on an explicit scene.
Its restoration checks protect later user changes. The explicit JobSession World
command wraps one verified saved asset with original-context checks and a durable
application claim. Recovered unapplied results, and completed results through a
separate reuse claim, now have shared native/MCP World approval and guarded
session-local restoration for saved PNG, JPEG and OpenEXR panoramas.
Panorama-specific generation and global undo integration remain.

Existing [image](../../scenario/blender/apply_image.py),
[3D import](../../scenario/blender/apply_3d.py),
[material](../../scenario/blender/apply_material.py),
[video](../../scenario/blender/apply_video.py) and
[audio](../../scenario/blender/apply_audio.py) application paths retain useful
behavior and native tests during integration. One provider job can return many
variants; use [primary-mesh selection](../../scenario/core/scene/placement.py)
instead of importing every asset as a separate result.

## Compatibility and proof

The approved floor is Blender 5.0. Check API availability at the supported
versions and validate the installed ZIP with the native test runner. Syntax
compatibility, a manifest declaration and ZIP validation are separate from
successful native execution. UI changes additionally need actual focus,
keyboard, viewport and screenshot review; headless tests cannot establish that.

## Saved media strips

[`media_application.py`](../../scenario/blender/media_application.py) is the
shared saved-result primitive for MP4/WebM movie and MP3/WAV/OGG sound strips.
It snapshots and rehashes a bounded local receipt before decoding on Blender's
main thread, keeps existing strips and timing unchanged, and rolls back only
new data. Its persistent file remains necessary for the strip. The
[JobSession command](../BLENDER_JOB_CONTEXT.md#explicit-saved-video-and-audio-application)
adds exact scene/frame approval, a durable claim and receipt-only recovery.
Prototype video/audio operators remain separate; they are not the entry points
for newly generated shared jobs.

## Saved models

[`model_application.py`](../../scenario/blender/model_application.py) stages one
receipt-bound embedded GLB in a disposable scene, then publishes a new
collection/group at an approved cursor. It preserves the original selection and
packs embedded textures, retains rigs and node/morph animation clips, and keeps
the destination timeline unchanged. The [model guide](../MESH_APPLICATION.md#explicit-saved-glb-import)
details supported containers, bounded synchronous work and rollback. Existing
`mesh_application.py` remains the separate explicit in-place mesh/UV primitive;
importing a new GLB does not establish those edit workflows.

## Saved materials

[`material_application.py`](../../scenario/blender/material_application.py)
loads only unambiguous receipt-bound texture maps into new packed images and a
new material. It assigns one approved mesh slot, preserving old material data,
other slots and face indices. The [material guide](../MATERIAL_APPLICATION.md)
details target restrictions, bounded decoding, rollback and receipt-only recovery.
Native and MCP actions share the scoped session; prototype material callbacks
are not used for this saved-result command.

## Film shot scenes

[`film_scene.py`](../../scenario/blender/film_scene.py) provides transactional local
shot construction and editable scene-strip timeline assembly. It validates the
whole recipe before mutation, uses receipt-checked GLB import for explicit heroes,
restores the working scene and removes newly created data on failure. See the
[Film primitive contract](../FILM_PLAN.md#native-shot-and-timeline-primitives) for
choreography, source identity and remaining shared-command approval requirements.
It does not bypass those requirements by exposing an unclaimed UI/MCP importer.

## Local render snapshots

[`local_capture.py`](../../scenario/blender/local_capture.py) writes the selected
local scene and dependencies to a private blend file without saving or changing
the working file. Only this snapshot step touches the parent's bpy state.
The [local render primitive](../FILM_PLAN.md#local-capture-foundation) owns its
offline child process and disposable profile; its standalone worker changes
render settings only in that child. Still capture does not require ffmpeg.
The [Film capture owner](../FILM_PLAN.md#shared-capture-and-upload-approval) now
binds native/MCP approval to the recipe and selected shot, queues work through
the existing session and accepts completion only in the unchanged original
context. Separate upload approval hashes the staged bytes against the rendered
receipt. The session joins workers before cleaning retained capture artifacts;
no bpy mutation runs on a worker or during drawing.

## Film saved-media review

[`film_review.py`](../../scenario/blender/film_review.py) provides transactional
local final/previs sequence assembly from explicitly scoped, measured receipts.
It rehashes independent copies before movie/audio decoding, preserves the working
scene and removes only new data on a fully rolled-back failure. Copies persist
for successful sequences and remain available after uncertain cleanup. Native
trims, audio loop/duck segments and optional muted masters are covered by installed
fixtures. It requires matching movie/cut frame rates. The [review contract](../FILM_PLAN.md#native-saved-media-review-primitive)
describes byte/strip limits. Its shared session command now supplies worker
preparation and generated-source claims before native decoding. Private copy
identities are rechecked around decoding without GUI-thread copying or hashing.
Session-owned [native/MCP review controls](../FILM_PLAN.md#native-and-mcp-review-controls)
separate preparation from the build approval. Drawing reads cached status, the
maintenance pump advances work, and the build runs on the main thread only in
Object Mode in a Blender window. Portable export and live/desktop acceptance
remain pending.
