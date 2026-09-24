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
application claim. Panorama generation, history and active UI/MCP wiring remain.

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
