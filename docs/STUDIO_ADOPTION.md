# Studio source and capability adoption

This is the source selection and implementation inventory for
[#64](https://github.com/scenario-labs/blender-plugin/issues/64). It records what
to bring into the canonical extension and which issue owns the remaining work.
It does not establish that Studio has been imported or that its runtime has
passed the canonical native tests.

## Selected source

Select Studio commit
[`e2b0277064f0c502d46524fba1d006d0ac83f846`](https://github.com/edemaistre/scenario-blender-studio/commit/e2b0277064f0c502d46524fba1d006d0ac83f846),
whose extension manifest declares **0.1.5**. Source inspection compares it with
canonical commit
[`3265dd5`](https://github.com/scenario-labs/blender-plugin/commit/3265dd5).

The selected commit is ten commits after the previously inspected Studio
`bfeac2873f3a3cb9e2bef1fdf97a14431ce4c65f`. Those commits change documentation,
website assets and validation evidence. The runtime, tests, packaging script
and third-party notice file are unchanged. In both revisions the Git tree IDs are:

| Source path | Git tree ID |
| --- | --- |
| `src/scenario_studio` | `e9db0dc9f820a3e52eda07a7aaea0b7d8171efa1` |
| `tests` | `5d7f983ca4c0316189df5609fc6b5ea45f0e5318` |

Reproduce that comparison in a Studio checkout:

```sh
git diff --exit-code bfeac2873f3a3cb9e2bef1fdf97a14431ce4c65f e2b0277064f0c502d46524fba1d006d0ac83f846 -- src tests scripts/package_plugin.py THIRD_PARTY_NOTICES.md
git rev-parse e2b0277064f0c502d46524fba1d006d0ac83f846:src/scenario_studio
git rev-parse e2b0277064f0c502d46524fba1d006d0ac83f846:tests
```

Upstream paths below refer to this exact revision, not a moving branch. The
source repository requires access; the provenance links do not grant it.

## One package and build

Keep `scenario/` as the only extension package, manifest ID `scenario`, display
name `Scenario`, and minimum Blender version `5.0.0`. Studio names an optional
expanded view, not another installable extension. Organize adopted pure Python
under `scenario/core/`, Blender integration under `scenario/blender/`, and the
existing local server under `scenario/mcp/`. Do not add `src/scenario_studio` as
a second runtime or carry its registration alongside the canonical registration.

Keep [tools/build.py](../tools/build.py), [tools/install.py](../tools/install.py)
and [tools/test_blender.py](../tools/test_blender.py) as the build/install/native
test path, exposed through [Makefile](../Makefile). Extend these for SDK wheels
and notices. Do not adopt Studio's `scripts/package_plugin.py`, distribution
ZIPs or independent release/version tooling.

The canonical release baseline remains 0.9.9 at the inspected commit. Follow
[release-please-config.json](../release-please-config.json) and
[.release-please-manifest.json](../.release-please-manifest.json): release-please
updates the manifest and `scenario/__init__.py` together. Do not import Studio's
0.1.5 package version or its unrelated 0.1.0 tooling metadata. Releases retain
`blender-plugin-vX.Y.Z` tags and `scenario-X.Y.Z.zip` files. No version bump or
release is part of source selection.

## Capability decisions

**Retain** means preserve the capability and its useful regression tests while
adapting the implementation. **Replace** means use one new implementation of the
same responsibility. **Defer** means the capability is not accepted in the
consolidated baseline; the named issue or roadmap item owns the follow-up.
Owners below are implementation issues, not assumed individual assignees.

Canonical paths are relative to the repository root. Studio module names are
relative to `src/scenario_studio/` at the selected revision.

| Capability | Decision and source | Owner and acceptance boundary |
| --- | --- | --- |
| Image, video, 3D, audio and material generation | Retain Studio's catalog/form/result flow (`catalog.py`, `schema.py`, `studio.py`); replace both service clients. | #64 adapter; #65 shared commands; #66 views. Preserve all existing generation lanes and verify each through the shared commands. |
| Catalog and trained/custom models | Retain Studio pagination, deduplication, cursor-loop rejection and `schema.prepare_run` routing; replace the canonical blanket trained-model exclusion in `scenario/core/api/catalog.py`. | #64 mapping; roadmap#674 G01 for complete trained/custom-model acceptance. A remote-MCP schema wrapper is not proof that REST exposes equivalent routing. |
| Conditional parameters and model switching | Retain `scenario/core/schema/params.py` conditional/one-of rules, default overrides and current-collection lookup in `scenario/blender/params_ui.py`; reconcile with Studio schema normalization. | #64/#66. Preserve `test_params`, `test_param_overrides` and native `test_params_ui` regressions, including callbacks Blender can otherwise swallow. |
| Compact composer, sidebar and expanded view | Replace the old composer presentation with Studio controls/layout/text input adapted to the compact-default contract; retain a useful native sidebar. | #66. Native focus, Unicode/IME, resizing, DPI, viewport passthrough and view switching remain required. Opening a view must not start another job engine. |
| Exact estimates and paid submission | Retain Studio quote fingerprint/invalidation and ambiguous-submission behavior; replace transport and spend boundary with shared SDK commands. | #64/#65. Preserve exact decimal quote data, scope and payload; persist request identity before dispatch; no blind retry. |
| Jobs, cancellation and history | Replace `studio.py`/`tasks.py` lifetime ownership and `scenario/core/jobs/manager.py` with one shared runtime; retain progress, results and recovery capabilities. | #65. Atomic versioned persistence, write failures, cancellation races, restart and UI-close tests are acceptance gates. |
| API keys, OAuth and project selection | Replace Studio `storage.py` credential/path handling and canonical preference-only auth with explicitly scoped adapter configuration and browser sign-in. | #67 and roadmap#692. API-key project ID stays optional and is passed when supplied; OAuth token acceptance requires its own verification. |
| Authenticated local MCP | Retain `scenario/mcp/{protocol,server,stdio_shim,sandbox}.py`, scene tools and `scenario/blender/mcp_service.py`; replace service-tool internals with shared commands. | #65; related #15/#17/#43/#44/#52/#53. Main-thread bpy, session auth, opt-in Python and safe captures remain mandatory. Studio's remote-MCP client is not this server. |
| Capture and references | Retain viewport/camera stills, selected-mesh export and reference attachment from `scenario/blender/{capture,mesh_export}.py` and Studio `scene.py`/`studio.py`. | #64/#65. Preserve render/selection state, private temporary files, main-thread capture and upload/result scope. |
| Render Image / Render Video | Retain `scenario/blender/render_lanes.py`, capture duration/frame planning and reference/prompt wiring; combine with Studio background render support. | #64/#65. Preserve first-frame/style inputs and model duration constraints; test encoding failures separately from service failures. |
| Camera tools | Retain canonical waypoint/marker editing and camera presets in `scenario/core/scene/shot_plan.py` and `scenario/blender/shot_planner.py`; reconcile Studio `scene.create_camera_path`. | #64. Preserve existing animation protections and camera tests; do not replace the preset library with a smaller unverified subset. |
| Blockout and scene plans | Retain canonical plan parsing/building and Studio `scene_plan.py`/`scene.py` validation and local planning. | #64; roadmap#674 G15 owns generated-object replacement expansion. Preserve full text-asset retrieval when previews are truncated. Paid plan generation stays behind the shared spend boundary. |
| Image application | Retain datablock load/pack, image editor, plane and material application from `scenario/blender/apply_image.py`; reconcile Studio `scene.import_asset`. | #64/#65. Explicit origin/target identity and failed-apply recovery; retain native image application tests. |
| 3D imports and mesh edits | Retain canonical primary-mesh ranking, PBR variant preference, job tagging and placement in `scenario/core/scene/placement.py` and `scenario/blender/apply_3d.py`; reconcile Studio format/import checks. | #64/#65; roadmap#674 G04 owns full in-place edit acceptance. Preserve mesh export and remesh/retexture/UV/rig/animate/parts routing without importing each variant as another object. |
| Gaussian splats | Retain `scenario/core/scene/spz.py` and `scenario/blender/apply_splat.py`; Studio's generic PLY importer does not replace SPZ decoding or splat presentation. | #64. Preserve `test_spz` and native `test_splat_and_reload`; validate point limits and axis conversion in the adopted package. |
| PBR materials | Retain canonical typed-map assignment, color spaces, smoothness inversion, normal/displacement nodes and Studio `materials.py`/`scene.apply_pbr_maps`. | #64. Reconcile map semantics with `test_material_plan`, `test_apply_material` and Studio material tests before removing either path. |
| HDRI/world application | Retain Studio `scene.apply_world`/`restore_world` and supported HDR image handling. | #64; roadmap#674 G03 owns complete skybox generation/application acceptance. Verify restoration and world-node behavior natively. |
| Video/audio preview and sequencer | Retain `scenario/blender/apply_video.py`/`apply_audio.py`, Studio media imports and preview controls. | #64; roadmap#674 G06/G22 own deeper sequencer/audio work. Test actual Blender APIs and missing external tools. |
| Prompt Spark, rewrite and translation | Retain canonical `scenario/core/api/{spark,llm}.py` behavior and `scenario/blender/prompt_tools.py`, plus Studio's quoted Spark flow. Replace service calls. | #64/#65. Prompt helpers can spend; UI and MCP must share preparation and approval semantics. |
| Asset library, search and organization | Retain Studio library/search/result organization (`studio.py`, `organization.py`) through typed adapter operations. Replace generic remote catalog execution. | #64 adapter; #65 scope. Verify collection/tag writes and uncertain outcomes without replaying a write automatically. |
| Workflows | Retain Studio workflow catalog, input form and estimate/run capabilities. Replace the remote-MCP and public-workflow raw HTTP paths. | #64/#65; roadmap#674 G09 owns broader workflow work. Verify public/private pagination, workflow schema and cancellation independently. |
| Automatic previews and progress | Retain 0.1.5 progress/result feedback and `previews.py`/`preview_worker.py`; route downloads through shared transfer policy. | #64/#65/#66. Bound resources, isolate child Blender profiles and keep job processing independent of preview/view lifetime. |
| Film | Retain useful `film*.py` planning, review, scene, finishing and export capabilities in optional expanded Studio, subject to the same adapter/runtime gates. Defer general Film authoring and product acceptance. | #64 import; #65 runtime; #66 view; #68 acceptance. Sample-specific assumptions and media dependencies remain experimental. |
| Chat, projection texturing and realtime restyling | Defer; do not infer these from Studio paint/overlay primitives. | roadmap#674 G13/G18/G23, after their prerequisites and scope are resolved. |

Issue numbers refer to
[blender-plugin](https://github.com/scenario-labs/blender-plugin/issues);
G-items refer to [roadmap#674](https://github.com/scenario-labs/roadmap/issues/674).
The inventory preserves existing capabilities without declaring the broader
G-items complete.

## Source intake and provenance

The selected source history attributes runtime/test commits to **Emmanuel de
Maistre**. Preserve the original author and any existing contributor trailers
for each imported change. Record original commit IDs and source-to-destination
paths with the import; later mechanical and functional commits must remain
distinguishable. Do not claim source authorship for an adaptation or infer
additional authors from prose acknowledgements.

Use a reviewed file allowlist, rather than copying the repository wholesale:

- Adopt useful runtime modules and unit/native test contracts identified above.
  Adapt fixture imports to the canonical layout; native tests must load the
  verified installed ZIP. Do not copy historical pass counts as current evidence.
- Preserve GPL-3.0-or-later and first-party notices. Keep root `LICENSE` and
  `scenario/LICENSE` identical. Preserve upstream license/provenance metadata
  when source moves.
- Fonts require `resources/Poppins-OFL.txt`; Tabler SVG icons require
  `resources/Tabler-LICENSE.txt`. Carry their notices into the ZIP alongside used
  resources and record them in the canonical third-party notices. Review
  `resources/icons.json` references when pruning unused icons.
- Audit bundled `resources/models.json` and `resources/schemas.json` before use:
  retain only appropriate public metadata or synthetic offline fixtures, with
  schema refresh behavior. Review preview PNG provenance before including them.
- Exclude upstream `demo/`, `dist/`, `reports/`, `docs/validation/`, website media,
  account-specific exports, historical instruction files, dependency files and
  release workflows. Rewrite public user guidance against the adopted behavior.
- Normalize retained/imported Python in a separate mechanical change under #28
  before functional edits. Record its final squash SHA in
  `.git-blame-ignore-revs` only after merge. Enable full-tree lint when the
  retained canonical tree is clean; do not normalize discarded prototypes.

## Integration boundaries found in source

The following paths require deliberate replacement or adaptation:

- Studio `client.py` uses remote MCP for model/schema retrieval, generation,
  uploads, assets/jobs, team/project discovery, workflows and search. It also
  directly requests the public workflow REST endpoint. `organization.py` uses
  dynamic remote catalog operations for collections and asset tags/updates.
  Neither transport is an approved SDK exception.
- `studio.py` also downloads preview URLs directly in `_fetch_thumbnail`; audit
  transfers outside `client.py` as well. Signed storage transfers, browser
  authorization and extension update delivery are separate protocols, with
  explicit URL, redirect, credential and cleanup policies.
- `StudioApp.close()` closes its `TaskRunner`; history append errors in
  `_record()` are swallowed. These do not meet #65's job-lifetime and durable
  persistence requirements. Port useful state transitions without preserving
  view-owned workers or silent persistence failures.
- Studio `storage.data_directory()` uses its own platform-specific support
  directories. Inject paths from `bpy.utils.extension_path_user` at the Blender
  boundary. Pure Python remains bpy-free; no prototype data migration is needed.
- Studio declares Blender 5.2.0. Adapt native APIs to the approved 5.0 minimum
  and test 5.0/5.1/5.2; changing the manifest alone cannot establish compatibility.

The published SDK 2.1.0 remains the selected contract baseline. See
[SDK_ADOPTION.md](SDK_ADOPTION.md) for the exact artifact, executable contracts
and unresolved authentication issue. Before adapter implementation, map all
operations above to that artifact's public methods, parameters and wrappers.
In particular, verify REST model-schema/routing equivalence, discovery, search,
organization and multipart completion instead of assuming remote-MCP behavior
is available under a similar SDK method name. Only a reproduced gap and linked
SDK issue permit a narrow fallback with a removal condition.

### Local video result insertion

The active Generations video result now offers **Add video strip** through
[apply_video.py](../scenario/blender/apply_video.py). It imports picture frames
with Blender's native movie-strip API at the current scene frame, on a wholly
unused channel, skipping locked/muted channels. Existing timeline and scene
settings remain intact, and failed decoding rolls back the new strip/editor.
This is a bounded first-party implementation of the retained local media import
capability. It omits embedded audio and preserves source frame count at the scene
frame rate. Sequencer editing, automatic retiming, Film and external encoding
remain separate; this does not complete the media capability inventory.

## External media tools

Adopt **external, optional ffmpeg** for Studio's PNG-to-MP4 playblast encoding;
do not download or bundle an executable implicitly. Studio's
`scene.render_video_job` keeps frames/logs when ffmpeg is absent or encoding
fails, and `previews.render_preview` requires ffmpeg for video thumbnails.
`film_finish.py` also discovers ffprobe for media validation.

The adopted UI must check availability before starting an encoding-dependent
action, explain the affected action, and retain usable local frames after a
failure. Missing ffmpeg must not disable still capture, non-video generation or
imports. Keep ffprobe-dependent Film validation explicit when unavailable.
Use portable discovery and test present/missing tools, timeout/cancellation and
child-process cleanup on supported platforms under #64/#31. These are adoption
requirements, not claims that upstream already implements every check.

## Next implementation gates

1. Prepare a provenance-preserving source intake and separate mechanical
   normalization. Resolve module dependencies before deleting either prototype's
   behavior; do not ship two clients or job engines as the consolidated result.
2. Implement the SDK adapter and offline contracts for the audited operations;
   add explicit non-spending live checks under #41. SDK issue #26 and OAuth
   transport acceptance remain separate unresolved gates. Credentials alone do
   not authorize paid checks.
3. Package pinned SDK/transitive wheels and licenses, then exercise the actual
   installed bundle with Blender 5.0, 5.1 and 5.2. Retain the isolated exact-ZIP
   test runner and its profile/network protections throughout adoption.
4. Complete #65 scoped commands/persistence and #66/#67 UI/auth work before
   claiming UI/MCP parity. #68 owns integrated acceptance; #32/#45 and Windows,
   GUI, dependency OS/CPU coverage remain explicit follow-ups.

This inventory is source inspection and planning evidence only. No Studio
runtime, bundled dependency, live API or paid-generation acceptance is claimed.
