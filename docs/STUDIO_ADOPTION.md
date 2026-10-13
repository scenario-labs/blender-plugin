# Studio source and capability adoption

This is the source selection and implementation inventory that
[#64](https://github.com/scenario-labs/blender-plugin/issues/64) delivered in
0.10.0. It records what to bring into the canonical extension and which issue
owns the remaining work. #64, #65, #66 and #68 closed on 2026-10-13; the
remaining checks for these capabilities are in
[#440](https://github.com/scenario-labs/blender-plugin/issues/440).
It does not establish that Studio has been imported or that its runtime has
passed the canonical native tests.

## Selected source

Select Studio commit
[`204c847ad6f999e1050070a35e58af666b28ff9c`](https://github.com/edemaistre/scenario-blender-studio/tree/204c847ad6f999e1050070a35e58af666b28ff9c),
tag `v0.2.0`, whose extension manifest declares **0.2.0**. On 2026-10-13 it was
the upstream `main` with no later push. The source repository is public.
Upstream paths below refer to this exact revision, not a moving branch.

It is one squashed commit after the 0.1.5 revision
[`e2b0277064f0c502d46524fba1d006d0ac83f846`](https://github.com/edemaistre/scenario-blender-studio/commit/e2b0277064f0c502d46524fba1d006d0ac83f846)
that the capability decisions below were first made against. It adds 43 modules
under `src/scenario_studio/` and changes 23 more, including a second local MCP
server (`bridge/`) and a second native N-panel registration (`sidebar/`). It
removes the demos, distribution ZIPs, reports and website. The bundled
`resources/`, the package `LICENSE.txt` and `THIRD_PARTY_NOTICES.md` are
byte-identical to 0.1.5. Every module the table names exists at both revisions.
The 0.2.0 differences and their owners are summarized in
[Studio 0.2.0 additions](#studio-020-additions).

| Source path | 0.1.5 Git tree ID | 0.2.0 Git tree ID |
| --- | --- | --- |
| `src/scenario_studio` | `e9db0dc9f820a3e52eda07a7aaea0b7d8171efa1` | `a2aa89b773972e7d9470eca572fa4cb86c7e1275` |
| `tests` | `5d7f983ca4c0316189df5609fc6b5ea45f0e5318` | `59fe4b46a0b70082cbf1418ffcf1be6ed0b14d23` |
| `src/scenario_studio/resources` | `507b4863cd5f5ea51360cb06c8566794b52bfa92` | unchanged |

Reproduce these identities in a Studio checkout:

```sh
git rev-parse 'v0.2.0^{commit}'
git rev-parse 204c847ad6f999e1050070a35e58af666b28ff9c:src/scenario_studio
git rev-parse 204c847ad6f999e1050070a35e58af666b28ff9c:tests
git diff --exit-code e2b0277064f0c502d46524fba1d006d0ac83f846 204c847ad6f999e1050070a35e58af666b28ff9c -- src/scenario_studio/resources src/scenario_studio/LICENSE.txt THIRD_PARTY_NOTICES.md
```

Adaptations already merged keep the revision they came from: the sections below
that name `e2b0277064f0c502d46524fba1d006d0ac83f846` record 0.1.5 provenance.

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
and notices. Do not adopt Studio's `Makefile`, `scripts/ci.sh`, `scripts/package.sh`,
`scripts/package_plugin.py`, manifest `[build]` table, distribution ZIPs or
independent release/version tooling.

The canonical release baseline is 0.10.0, published on 2026-10-13. Follow
[release-please-config.json](../release-please-config.json) and
[.release-please-manifest.json](../.release-please-manifest.json): release-please
updates the manifest and `scenario/__init__.py` together. Do not import Studio's
0.2.0 package version, its `version.py` or its tooling metadata. Releases retain
`blender-plugin-vX.Y.Z` tags and `scenario-X.Y.Z.zip` files. No version bump or
release is part of source selection.

## Capability decisions

**Retain** means preserve the capability and its useful regression tests while
adapting the implementation. **Replace** means use one new implementation of the
same responsibility. **Defer** means the capability is not accepted in the
consolidated baseline; the named issue or roadmap item owns the follow-up.
Owners below are implementation issues, not assumed individual assignees.

Canonical paths are relative to the repository root. Studio module names are
relative to `src/scenario_studio/`. The decisions were made against 0.1.5 and
reconciled with 0.2.0 on 2026-10-13; see [Studio 0.2.0 additions](#studio-020-additions).
#64, #65, #66 and #68 in the owner column are the issues that delivered these
capabilities in 0.10.0; the acceptance each row still lists continues in #440.

| Capability | Decision and source | Owner and acceptance boundary |
| --- | --- | --- |
| Image, video, 3D, audio and material generation | Retain Studio's catalog/form/result flow (`catalog.py`, `schema.py`, `studio.py`); replace both service clients. | #64 adapter; #65 shared commands; #66 views. Preserve all existing generation lanes and verify each through the shared commands. |
| Catalog and trained/custom models | Retain Studio pagination, deduplication, cursor-loop rejection and `schema.prepare_run` routing; replace the canonical blanket trained-model exclusion in `scenario/core/api/catalog.py`. | #64 mapping; roadmap#674 G01 for complete trained/custom-model acceptance. A remote-MCP schema wrapper is not proof that REST exposes equivalent routing. |
| Conditional parameters and model switching | Retain `scenario/core/schema/params.py` conditional/one-of rules, default overrides and current-collection lookup in `scenario/blender/params_ui.py`; reconcile with Studio schema normalization. | #64/#66. Preserve `test_params`, `test_param_overrides` and native `test_params_ui` regressions, including callbacks Blender can otherwise swallow. |
| Compact composer, sidebar and expanded view | Replace the old composer presentation with Studio controls/layout/text input adapted to the compact-default contract; retain a useful native sidebar. | #66. Native focus, Unicode/IME, resizing, DPI, viewport passthrough and view switching remain required. Opening a view must not start another job engine. The compact composer now shows the current job and its explicit result actions; its dialogs opened from the composer still need desktop proof. |
| Exact estimates and paid submission | Retain Studio quote fingerprint/invalidation and ambiguous-submission behavior; replace transport and spend boundary with shared SDK commands. | #64/#65. Preserve exact decimal quote data, scope and payload; persist request identity before dispatch; no blind retry. |
| Jobs, cancellation and history | Replace `studio.py`/`tasks.py` lifetime ownership and `scenario/core/jobs/manager.py` with one shared runtime; retain progress, results and recovery capabilities. | #65. Atomic versioned persistence, write failures, cancellation races, restart and UI-close tests are acceptance gates. |
| API keys, OAuth and project selection | Replace Studio `storage.py` credential/path handling with explicitly selected API-key credentials and scoped adapter configuration. The current preferences expose an optional Project ID. | API-key runtime shipped in 0.10.0 (#65); live project permission and a project switch continue in #440. Browser sign-in is deferred under #67 and roadmap#692; OAuth token acceptance requires separate verification. |
| Authenticated local MCP | Retain `scenario/mcp/{protocol,server,stdio_shim,sandbox}.py`, scene tools and `scenario/blender/mcp_service.py`; replace service-tool internals with shared commands. | #65; related #15/#17/#43/#44/#52/#53. Main-thread bpy, session auth, opt-in Python and safe captures remain mandatory. Studio's remote-MCP client is not this server. |
| Capture and references | Retain viewport/camera stills, selected-mesh export and reference attachment from `scenario/blender/{capture,mesh_export}.py` and Studio `scene.py`/`studio.py`. | #64/#65. Preserve render/selection state, private temporary files, main-thread capture and upload/result scope. |
| Render Image / Render Video | Retain `scenario/blender/render_lanes.py`, capture duration/frame planning and reference/prompt wiring; combine with Studio background render support. | #64/#65. Preserve first-frame/style inputs and model duration constraints; test encoding failures separately from service failures. The saved-image first-frame handoff is restored as an approved native and MCP action that reuses the result's asset ID; paid render runs passed for 0.10.0, and the handoff and clip capture on Blender 5.0 and 5.2 continue in #440. |
| Camera tools | Retain canonical waypoint/marker editing and camera presets in `scenario/core/scene/shot_plan.py` and `scenario/blender/shot_planner.py`; reconcile Studio `scene.create_camera_path`. | #64. Preserve existing animation protections and camera tests; do not replace the preset library with a smaller unverified subset. |
| Blockout and scene plans | Retain canonical plan parsing/building and Studio `scene_plan.py`/`scene.py` validation and local planning. | #64; roadmap#674 G15 owns generated-object replacement expansion. Preserve full text-asset retrieval when previews are truncated. Paid plan generation stays behind the shared spend boundary. |
| Image application | Retain datablock load/pack, image editor, plane and material application from `scenario/blender/apply_image.py`; reconcile Studio `scene.import_asset`. | #64/#65. Explicit origin/target identity and failed-apply recovery; retain native image application tests. |
| 3D imports and mesh edits | Retain canonical primary-mesh ranking, PBR variant preference, job tagging and placement in `scenario/core/scene/placement.py` and `scenario/blender/apply_3d.py`; reconcile Studio format/import checks. Shared saved jobs now classify GLB, glTF, FBX, OBJ and mesh PLY results into ordered import units with one explicit, receipt-checked import per unit; the prototype **Add to scene** path is unchanged. | #64/#65; roadmap#674 G04 owns full in-place edit acceptance. Preserve mesh export and remesh/retexture/UV/rig/animate/parts routing without importing each variant as another object. Live provider package shapes and desktop review of the new controls remain. |
| Gaussian splats | Retain `scenario/core/scene/spz.py` and `scenario/blender/apply_splat.py`; Studio's generic PLY importer does not replace SPZ decoding or splat presentation. Shared saved jobs now decode SPZ, `.splat` and Gaussian PLY results on a worker and build a new point cloud (mesh plus Geometry Nodes and a new material, never one reused by name) at an approved cursor with reviewed point limits and axes; the prototype SPZ import delegates to the same builder. | #64/#65. Preserve `test_spz`, native `test_splat_and_reload` and `test_splat_application`; live provider files, default axes and desktop review of the splat options remain. |
| PBR materials | Retain canonical typed-map assignment, color spaces, smoothness inversion, normal/displacement nodes and Studio `materials.py`/`scene.apply_pbr_maps`. | #64. Reconcile map semantics with `test_material_plan`, `test_apply_material` and Studio material tests before removing either path. |
| HDRI/world application | Retain Studio `scene.apply_world`/`restore_world` and supported HDR image handling. The Environment lane (sidebar, Studio Create, the composer's Generate mode and local MCP) now generates panoramas, HDRIs and upscales through verified skybox model contracts; results wait for explicit World approval and a saved LDR panorama offers a Make HDRI form prefill. | #64, #98; roadmap#674 G03 owns broader skybox work. Paid Flux 360, HDRi Skybox, upscale and Skybox GPT runs passed for 0.10.0; HY World output, seam, pole and HDR range review and the desktop recheck of the merged lane continue in #440. Verify restoration and world-node behavior natively. |
| Video/audio preview and sequencer | Retain `scenario/blender/apply_video.py`/`apply_audio.py`, Studio media imports and preview controls. Saved shared results add receipt-bound Play, Play in Blender and waveform controls in `scenario/blender/result_media.py`. | #64; roadmap#674 G06/G22 own deeper sequencer/audio work. Test actual Blender APIs and missing external tools; listening passed on 2026-10-13, and the waveform follow-ups continue in #440. |
| Prompt Spark, rewrite and translation | Retain New, Rewrite and Translate through `scenario/blender/prompt_jobs.py`, shared SDK commands and complete text retrieval in `scenario/core/jobs/results.py`. Obsolete Spark/LLM service modules and automatic paid fallback are removed. | #64/#65. Prompt helpers share explicit quote/approval and durable submission across UI/MCP; live output acceptance remains. |
| Asset library, search and organization | Retain Studio library/search/result organization (`studio.py`, `organization.py`) through typed adapter operations. Replace generic remote catalog execution. | #64 adapter; #65 scope. Verify collection/tag writes and uncertain outcomes without replaying a write automatically. |
| Workflows | Retain Studio workflow catalog, input form and estimate/run capabilities. Replace the remote-MCP and public-workflow raw HTTP paths. | #64/#65; roadmap#674 G09 owns broader workflow work. Verify public/private pagination, workflow schema and cancellation independently. |
| Automatic previews and progress | Retain 0.1.5 progress/result feedback and `previews.py`/`preview_worker.py`; route downloads through shared transfer policy. | #64/#65/#66. Bound resources, isolate child Blender profiles and keep job processing independent of preview/view lifetime. Shared jobs now project validated in-memory remote progress into the sidebar and Studio Jobs views and MCP `job_status`, with the composer strip's words, and the compact composer's job strip shows the current job's status, progress and explicit actions. Automatic result previews show Scenario's preview images for video, 3D and audio and stills decoded from verified saved images in Jobs, Generations and Studio, without Studio's external ffmpeg or child GLB renders. Local MCP `inspect_result_previews` reports the same preview states, still metadata and audio envelopes. Live/desktop acceptance remains. |
| Film | Retain useful `film*.py` planning, review, scene, finishing and export capabilities in optional expanded Studio, subject to the same adapter/runtime gates. Defer general Film authoring and product acceptance. | #64 import; #65 runtime; #66 view; delivered in 0.10.0 as experimental. The Film desktop rerun, its production gaps and the criteria for lifting its experimental status are in #440. Sample-specific assumptions and media dependencies remain experimental. |
| Chat, projection texturing and realtime restyling | Defer; do not infer these from Studio paint/overlay primitives. | roadmap#674 G13/G18/G23, after their prerequisites and scope are resolved. |

Issue numbers refer to
[blender-plugin](https://github.com/scenario-labs/blender-plugin/issues);
G-items refer to [roadmap#674](https://github.com/scenario-labs/roadmap/issues/674).
The inventory preserves existing capabilities without declaring the broader
G-items complete.

## Studio 0.2.0 additions

The 2026-10-13 source review of 0.2.0 against canonical `main` at
`34ce22e8a4b037312334d98fbec6641da45a9a45` classified its new capabilities as
follows. Upstream test counts, headless checks and its paid run used Studio's own
package and remote-MCP client; they are not canonical evidence. Nothing listed
here is imported. The decisions in the table above still apply where they overlap.
#64, #65 and #66 closed as delivered in 0.10.0, so their remaining items are tracked
on #440.

| 0.2.0 capability | Decision | Owner |
| --- | --- | --- |
| Agent bridge (`bridge/`): loopback Streamable HTTP, token, typed tools, main-thread queue | Keep the canonical local server, which is already stricter on Origin, tokens, captures and errors. Do not ship a second server. Adapt its `Host` check, idle timeout and own-output file policy. | #440, #448 |
| Agent spending: off by default, per-job and per-session CU limits, reserve/settle ledger | Adapt as a scoped, exact-decimal switch and ledger that covers every paid MCP tool | #447 |
| Bridge scene binding, action log, guarded `undo_last`, form prefill for the user to submit | Adapt binding, log and prefill. Do not port `undo_last` as is: its scene hash misses mesh data, modifiers and keys. | #440 (roadmap#674 G19) |
| Native sidebar (`sidebar/`) | Already covered by the canonical panels and shared runtime. Do not add a second registration. | #440 |
| Text editing and key policy: word-grouped undo, shortcuts while typing, unfocused key blocking | Adapt undo and the typing pass-through set; decide the unfocused policy | #440 |
| Read retries, poll backoff, control and transfer lanes, resumable downloads | Adapt through SDK per-request retries and the shared transfer policy. Paid and mutating calls stay at zero retries. | #451, #453 |
| Unclear-submission block for the same request; estimate that returns a job | Adapt per credential scope | #452 |
| No-spend switch for QA runs | Adapt at the shared spend boundary | #440 |
| macOS Keychain secret, team/project picker, usage display, paste-key onboarding | Adapt with explicit selection and no inferred project; check the usage contract first | #67, roadmap#674 G08 |
| Library kind filters, newest-first order, thumbnails, job-card time and charged CU | Adapt through SDK filters and the preview lane | #440 |
| Redacted diagnostics export | Adapt with the allowlisted failure text, not regex redaction | #456 |
| Camera takes and "Back to my camera" | Adapt; first scope the shot camera per scene | #454, #440 |
| One render service with Blender's built-in H.264, progress and engine choice | Adapt in place of external ffmpeg for local capture | #440 |
| Asset slots, revisions and refit; appearance states | Defer until blockout replacement and a product decision; appearance states conflict with ownership checks | roadmap#674 G15, #440 |
| PBR options (DirectX normals, UV repeat, metalness override) | Adapt as explicit choices, never filename inference | #440 |
| Film hardening: prepare-only arming, ledger, scoped client, model adapter, recipe identity | Already covered by the shared job store and Film task bindings. Adapt the model-neutral duration rule, the recipe canvas size and the 0.2.0 recipe keys; keep text verbatim. | #440, #455 |
| Live findings: F12 renders the sequencer after media insertion; PATINA smoothness semantics | Both also apply to canonical | #449, #450 |

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
  resources and record their provenance in `scenario/icons/README.md`; the repository has no
  separate third-party notices file. Review `resources/icons.json` references
  when pruning unused icons. No new bundled asset arrived in 0.2.0.
- Audit bundled `resources/models.json` and `resources/schemas.json` before use:
  retain only appropriate public metadata or synthetic offline fixtures, with
  schema refresh behavior. Review preview PNG provenance before including them.
- Exclude upstream `demo/`, `dist/`, `reports/`, `docs/validation/`, website media,
  account-specific exports, historical instruction files, dependency files and
  release workflows. Rewrite public user guidance against the adopted behavior.
- Also exclude, from 0.2.0: `llms.txt`; `BUGS.md`, `ROADMAP.md` and `CHANGELOG.md`,
  which carry spend figures and a live job identifier (triage them into issues
  instead); `docs/Agent Bridge.md` and `docs/Architecture.md` (rewrite against
  adopted behavior); and `scripts/live_*` and `scripts/gui_qa_*` (ideas only: they
  record a job identifier, assume macOS paths and read a stored credential file).
  The `scripts/test_blender_*.py` checks load the source tree, not the packaged
  ZIP; adapt them only as test contracts.
- 0.2.0 arrives as one squashed commit, so its provenance is that commit:
  record `204c847ad6f999e1050070a35e58af666b28ff9c` and the source path, and keep
  its author and existing co-author trailer. Its Python files carry no SPDX
  headers; adapted files take the canonical headers plus the attribution note
  that existing adaptations use.
- The tree was normalized under #28 and CI lints all of it. Format newly
  imported Python in a separate mechanical change before functional edits, and
  record its final squash SHA in `.git-blame-ignore-revs` only after merge.
  Do not normalize discarded prototypes.

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

The published SDK 2.2.0 remains the selected contract baseline. See
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
An empty workspace sequencer scene selector is initialized to the destination;
an existing selection remains unchanged.
This is a bounded first-party implementation of the retained local media import
capability. It omits embedded audio and preserves source frame count at the scene
frame rate. Sequencer editing, automatic retiming, Film and external encoding
remain separate; this does not complete the media capability inventory.

## Adopted Film planning contracts

The 0.1.5 source's pure Film recipe and scene-plan helpers and their tests are
now relocated into `scenario/core/scene/film_plan.py` and `film_scene_plan.py`.
Source intake and mechanical normalization remain separate commits with the
original author preserved. The API-key adaptation makes recipe project selection
optional and resolves task assets only within the exact selected job scope.
See the [Film contract guide](FILM_PLAN.md) for timing, audio, scene-schema limits
and explicit remaining integration. No Studio runner, client, separate storage,
view registration, media binary or sample media is imported by this step.

## Native Film scene construction

The first-party [Film scene primitive](../scenario/blender/film_scene.py) implements
the retained shot/timeline responsibilities identified in the selected Studio
`src/scenario_studio/film_scene.py` and scene adapter at
`e2b0277064f0c502d46524fba1d006d0ac83f846`: editable primitives and cameras, role metadata,
hero placement and animation, and a director sequence. It uses current validated
recipe contracts, data-based geometry construction and the existing receipt-bound
GLB importer. Motion/NLA choreography is adapted from Emmanuel de Maistre's
selected source; attribution is retained with the adaptation. Geometry creation,
receipt preflight, transaction cleanup and scene identity checks use the current
package's contracts. No prototype file-path importer, global source-asset cache, transport,
production-state file, snapshot history or automatic project save is carried over.
Actor geometry/rig/morph data are independent, trading extra import/memory cost for
explicit instance isolation. Shared Film application claims and controls are the
next integration boundary; this local component is not completed Film acceptance.

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

[`installed_tools.py`](../scenario/core/jobs/installed_tools.py) is the shared,
bpy-free lookup for `ffmpeg` and `ffprobe`. MP4 capture, Film media inspection,
export verification and the export dialog's verification name all use it. It
checks the current PATH first, then fixed install folders: `/opt/homebrew/bin`,
`/usr/local/bin` and `/opt/local/bin` on macOS, `/usr/local/bin` and `/usr/bin`
on Linux. Windows uses PATH only. Blender opened from the macOS Dock or Finder
gets launchd's PATH, `/usr/bin:/bin:/usr/sbin:/sbin`, which lacks Homebrew and
MacPorts. Lookup accepts only executable regular files and returns their resolved
absolute path. It never changes the environment, runs a program, or uses a match
from the working directory or a relative PATH entry. On Windows, `shutil.which`
searches the working directory first and stops at a match there; lookup then
checks each absolute PATH folder directly, with PATHEXT. `/snap/bin` is excluded:
a strictly confined snap's home access excludes the hidden extension storage
these tools read. No preference or environment variable selects another tool
path. A missing tool's error names it, lists the places searched and, on macOS,
says that apps opened from the Dock or Finder do not inherit the shell PATH.

The first-party [Film video export](FILM_PLAN.md#offline-film-video-export-primitive)
needs no external encoder: an offline Blender child uses Blender's built-in
FFmpeg. An installed ffprobe adds a full decoded-frame check; without it, a
second Blender child performs a weaker decode check and the receipt records which
verification ran. This MP4 export, and its
[native/MCP controls](FILM_PLAN.md#native-and-mcp-video-export-controls) under
Film > Export and the Studio Film Review page, are new first-party code, not an
adaptation of Studio's `film_export.py` or its UI. They do not replace Studio's
retained case-study bundle (the Film row above); the
[case-study adaptation](#film-case-study-bundle-adaptation) below provides it.

## Local background capture adaptation

The first-party PNG/playblast responsibility from selected Studio
`src/scenario_studio/scene.py` (`prepare_video_render`/`render_video_job`) and
`src/scenario_studio/render_worker.py` is adapted into
[`local_capture.py`](../scenario/blender/local_capture.py),
[`local_render.py`](../scenario/core/jobs/local_render.py) and the bundled
[`render_worker.py`](../scenario/blender/render_worker.py).
The source revision is `e2b0277064f0c502d46524fba1d006d0ac83f846`;
Emmanuel de Maistre's source attribution and GPL notices are preserved.
This is a functional adaptation, not a wholesale relocation or mechanical
normalization of the upstream runtime.

The current implementation exports only the selected scene/dependencies with
`bpy.data.libraries.write`, binds the snapshot hash, runs an offline child with
a disposable profile, requires exact frames and validates the encoded media.
It preserves the selected Workbench styling and optional external encoder
approach without adopting Studio's task runner, production storage, automatic
save, service client or implicit upload. No media executable or sample asset is
imported. The [capture contract](FILM_PLAN.md#local-capture-foundation) distinguishes
retained diagnostic/media files from child scratch cleanup. The
[shared capture owner](FILM_PLAN.md#shared-capture-and-upload-approval) now
integrates explicit native/MCP rendering, cancellation and separate upload
approval on the existing session. Finishing/export and native desktop acceptance
remain separate.

## Composition planning adaptation

The unpaid composition responsibility from selected Studio
`src/scenario_studio/film_finish.py` at
`e2b0277064f0c502d46524fba1d006d0ac83f846` is adapted into
[`core/scene/film_finish.py`](../scenario/core/scene/film_finish.py).
Emmanuel de Maistre's source attribution is retained. Exact cut timing, selected
takes, source trims, native volume, separate previs/final modes, audio loop phase
and duck segments are preserved. This is a functional adaptation, not a wholesale
relocation of the original module or its prototype records.

The new [scoped draft reader](../scenario/core/jobs/film_finishing.py) reuses the
shared job/upload stores and rejects stale or ambiguous source observations.
Audio duration is supplied as an asset-bound exact observation; no path fallback,
implicit media probe, legacy production storage, organizer client, VSE mutation
or automatic generation is imported. The [draft contract](FILM_PLAN.md#unpaid-composition-drafts)
keeps active controls, final review/export and live acceptance as explicit
remaining work. The new [verified-media command](FILM_PLAN.md#verified-media-preparation)
implements explicit receipt-bound measurement through the shared session and
workers. It uses an optional installed ffprobe, private copies and current-source
checks instead of importing the prototype's unchecked file-path or duration cache.
No new third-party dependency or service operation is added.

## Native saved-media review adaptation

The local `build_review_scene` responsibility from selected Studio
`src/scenario_studio/film_finish.py` at
`e2b0277064f0c502d46524fba1d006d0ac83f846` is adapted into
[`blender/film_review.py`](../scenario/blender/film_review.py), retaining Emmanuel
de Maistre's attribution. Picture/source trims, native audio gain, editorial
loop phase and ducking, continuity metadata and optional muted master comparison
remain. The new primitive also supports a previs cut.

Prototype record/path fallbacks and scene switching are replaced by explicit
scoped receipts, measured metadata, independent hashed copies and transactional
rollback that preserves the working scene. Silent video is handled without an
invalid sound strip. Matching movie/cut frame rates are required until explicit
normalization is implemented. The [contract](FILM_PLAN.md#native-saved-media-review-primitive)
records limits and installed synthetic tests. The shared session now prepares
independent copies on existing workers and separately approves native application
with generated-source claims and receipt-only recovery. First-party
[native/MCP review controls](FILM_PLAN.md#native-and-mcp-review-controls) expose
those commands in the sidebar, the Studio Film **Review** page and local MCP, with
separate preparation and build approvals; no Studio UI code is copied for them.
First-party [native/MCP video export controls](FILM_PLAN.md#native-and-mcp-video-export-controls)
over the [export primitive](FILM_PLAN.md#offline-film-video-export-primitive)
render a built review scene to MP4. The retained case-study bundle is adapted
separately below; provider/desktop acceptance remains separate, and no prototype
client or production storage is imported.

## Film case-study bundle adaptation

The case-study responsibility of selected Studio `src/scenario_studio/film_export.py`
(`export_case_study`, `approved_task_ids`, `sanitized_ledger`, `sanitized_recipe`
and its opening guide) at `e2b0277064f0c502d46524fba1d006d0ac83f846`, triggered
from Studio's `film_ui.py` and `film.py`, is adapted into
[`core/scene/film_case_study.py`](../scenario/core/scene/film_case_study.py),
[`core/jobs/local_case_study.py`](../scenario/core/jobs/local_case_study.py),
[`blender/film_case_study.py`](../scenario/blender/film_case_study.py), the bundled
[`film_case_study_worker.py`](../scenario/blender/film_case_study_worker.py) and
[native controls](../scenario/blender/film_case_study_controls.py). Emmanuel de
Maistre's source attribution is retained in those modules, in the bundle manifest
and in its opening guide. The approved-take selection, the credential and URL
sanitizer, the curated scenes with bundle-relative media and packed textures, the
recipe, ledger and manifest documents and the opening steps follow that source,
and its export tests are adapted into the canonical unit tests. This is a
functional adaptation, not a relocation of the original module.

The adaptation keeps the working file unchanged: an offline child rewrites a
private snapshot instead of temporarily rewriting and restoring the user's own
paths and packing state. It also rebuilds sound strips whose hidden paths Blender
cannot otherwise rewrite, removes Scenario properties that identify jobs, assets
or productions and the extension's saved settings, verifies the written library in
a second child and packs one ZIP saved with the video export's approval,
verification and never-overwrite publish.
The ledger keeps the maintainer-approved scope: titles, kinds, models, provenance,
saved states, exact quoted costs and result media types, without the request, job,
asset, project or team identifiers, URLs or paths the source ledger kept. Studio's
director-timeline validation becomes a blocking reason, a previs review may be
bundled as well as a final one, and the timeline is optional. See the
[bundle contract](FILM_PLAN.md#portable-case-study-bundle). No Studio client,
production storage, media binary or sample media is imported.

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
4. The scoped commands, persistence and views shipped in 0.10.0 (#65, #66).
   API-key authentication is the release path; #67 OAuth is deferred. #32
   native baseline CI and #45 required-check administration are closed; the open
   desktop and live checks are in #440.

This inventory preserves capability decisions and scoped implementation updates.
The [release acceptance record](maintenance/release-acceptance.md) identifies
current candidate tests and remaining gates; the source inventory alone does not
establish complete Studio, live API or paid-generation acceptance.


## Expanded native presentation

The first-party `scenario/blender/studio.py` view implements explicit expanded
navigation while reusing the current native creation, Film, job, result and
connection controls. It retains their scene form and shared runtime rather than
importing StudioApp's view-owned task runner or separate storage. Its page state
is unsaved WindowManager data, and no startup/file-load hook opens the view.
No selected-source runtime, font or icon is copied by this presentation layer.

This is a bounded adaptation of the retained expanded-view responsibility, not
complete source/UI adoption. Native workflow input/approval controls now reuse
the shared session. Native Library search and confirmed model/workflow-reference
reuse also use that session, as do explicit local-file and capture uploads into
workflow inputs (the retained Studio attach-file behavior). Asset organization
and broader compact composer replacement remain. Earlier Studio interaction evidence
covers prompt handoff/editing, populated-form scrolling, quote-preserving
navigation, continued saved-job polling, small-window fit and viewport return.
The new workflow and Library controls still need native interaction proof;
alternate-DPI and IME acceptance remain pending. The
[UI guide](UI_STYLE.md#explicit-studio-view) records those boundaries.
