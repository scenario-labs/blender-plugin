# Consolidated extension release acceptance

Release [#70](https://github.com/scenario-labs/blender-plugin/pull/70) remains on
hold under [#68](https://github.com/scenario-labs/blender-plugin/issues/68).
This record identifies the tested integration candidate and the evidence still
needed before releasing 0.10.0. It does not replace the
[release plan](release-plan.md), narrow retained-lane acceptance or authorize
publication. OAuth remains deferred under #67. The
[0.10.0 evidence by lane](#0100-evidence-by-lane) is the current summary; later
sections keep their own candidate identities and dates.

## 0.10.0 evidence by lane

Reviewed on 2026-10-12 against `main` at
`ff8d29d879487719fde8fd9b4089438ae0ba2c78`, after #421 merged, and brought up
to date with `main` at `df2fac37c5e605854718811ffaf74384d8341033`, after #411
merged. Since that first review, #403 to #406, #408 to #411, #416 to #420, #422
to #424, #426 and #428 have merged. Desktop checks found the preview pager and
composer progress bar defects that #423 and #424 fix, and the
[end-to-end production run](#end-to-end-production-run) found the media tool
lookup and Film review defects that #426 and #428 fix. Still open: #425
(reasons for failed jobs), #427 (MCP waits for a model description), #429
(local MCP scene changes mark the file modified) and release PR #70. The final
candidate is not built yet. This section records which evidence each retained
capability has, of which kind, and what remains with its owner. It does not
certify the final archive, authorize publication or close #68.

### Release candidate identity

| Item | Identity |
| --- | --- |
| Source commit | TODO(final candidate): the release-please commit that builds 0.10.0 |
| Package | `scenario-0.10.0.zip`, SHA-256 TODO(final candidate) |
| Hosted CI | TODO(final candidate): `ci-ok` run for that commit |
| Release workflow | TODO(final candidate): release run, its 5.1.2 and 5.2.1 validation jobs and attestations |
| Installed suite | TODO(final candidate): counts on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, with update and offline restart |

Until then, the latest integrated evidence is:

- `main` at `df2fac37` passes
  [hosted CI](https://github.com/scenario-labs/blender-plugin/actions/runs/38344728434):
  7,243 unit tests with the known SDK authentication expected failure on Python
  3.11 and 3.13, and 1,244 installed baseline tests per job, five skips each, on
  Linux x64 and Windows x64 with Blender 5.0.1, 5.1.2 and 5.2.1, with the same
  install, update and offline restart checks as the run below.
- `main` at `ff8d29d8` passes
  [hosted CI](https://github.com/scenario-labs/blender-plugin/actions/runs/38267887382):
  6,691 unit tests with the known SDK authentication expected failure on Python
  3.11 and 3.13, and 1,034 installed baseline tests per job on Linux x64 (Ubuntu
  24.04, five skips) and Windows x64 (Windows Server 2025, four skips) with
  Blender 5.0.1, 5.1.2 and 5.2.1. Each job also passes the native install and
  update fixture and the package update and offline restart check with a
  synthetic predecessor. Each job builds its own archive. These hosted runs are
  the accepted Linux and Windows evidence for this release; no desktop
  interaction ran on those platforms.
- A 0.10.0 build from release PR #70's head
  `0bb206efe29d7903b096b9c470673d3c572af565`, whose `scenario/` matches the
  corrected 0.9.9 candidate source below, produced ZIP SHA-256
  `e6740c84efbf1c1df981334742fc8c258704c1ab05ed4bee0bdaf6d2ac8a2a68`. On
  2026-10-10 it passed 1,149 installed tests with two Windows-only skips, and
  the synthetic update and offline restart, on each of macOS 27.0.1 arm64
  Blender 5.0.1, 5.1.2 and 5.2.1 LTS. It predates the lane pull requests from
  #352 onward, so it is a baseline, not the candidate.
- The weekly macOS arm64 and Windows x64 run on 2026-10-12 failed one stale
  expectation in `test_result_actions` on both platforms, one failure among
  1,369 tests with two skips on Blender 5.1.2; #396 corrected that test the
  same day. #399 and #400 stay open until a rerun passes. TODO(final
  candidate): the weekly or manual run on the final commit.

### Evidence kinds

| Kind | Meaning |
| --- | --- |
| Unit | Locked offline pytest, without Blender or network access. |
| Installed | The exact packaged ZIP in an isolated profile, `tools/test_blender.py --suite all`, with synthetic service responses; macOS 27.0.1 arm64 unless stated. |
| Hosted CI | `ci-ok`, including the Linux x64 and Windows x64 baseline on Blender 5.0.1, 5.1.2 and 5.2.1. |
| Desktop | An exact ZIP in a fresh profile, driven by real operating-system mouse and keyboard events on macOS 27.0.1 arm64 (Retina, French keyboard layout), with inspected screenshots. Blender 5.1.2 at UI scales 1.0 and 2.0 unless stated. A spend guard kept sessions free unless stated: reads, dry-run quotes and, where stated, free uploads. The paid desktop pass and the #424 recheck of 2026-10-13 ran without it, with generation authorized by the maintainer. |
| Free live | Real service reads, dry-run quotes, uploads or organization writes, without generation. |
| Paid live | Billed generation authorized beforehand by the maintainer for its scope and budget. The service reimburses failed generation jobs. |

Most desktop and live checks before 2026-10-13 ran on pre-merge pull request
heads, named per lane; the 2026-10-13 checks ran on `main`. Saved results
reached isolated profiles through read-only cloud recovery. Unit, installed and
hosted results for each merged pull request are in its description. Quote
values, saved identities and private reports stay private.

On 2026-10-13, besides the [preview pager check](#previews-and-playback), three
sessions on macOS arm64 with Blender 5.1.2 added evidence on `main`, named in
their lanes:

- the **paid desktop pass**: an exact ZIP built from `2e89cae8`, at UI scale
  1.0, with generation authorized by the maintainer;
- the **#423 and #424 recheck**: an exact ZIP built from `dad196a8`, at UI scales
  1.0 and 2.0, offline for the pager and with authorized generation for the
  progress bar;
- the [end-to-end production run](#end-to-end-production-run) through local MCP
  on `3720c9e3`.

### Lane summary

| Lane | Strongest evidence | Status |
| --- | --- | --- |
| [Image](#image) | Paid hosted smoke; free live quotes and UI/MCP parity on desktop | Passed |
| [Material](#material) | Paid hosted smoke; installed application on 5.0.1, 5.1.2 and 5.2.1 | Passed |
| [Render Image and Render Video](#render-image-and-render-video) | Paid live, including a first frame; desktop handoff, clip capture and ready quote | Passed |
| [Audio](#audio) | Paid hosted smoke; installed; desktop waveform | Pending: human listening |
| [3D generation and imports](#3d-generation-and-imports) | Paid hosted smoke; paid desktop FBX import; desktop GLB and OBJ imports | Pending: mesh PLY; no glTF JSON producer |
| [Splats](#splats) | Paid desktop SPZ generation and import; installed on 5.0.1, 5.1.2 and 5.2.1 | Pending: splat PLY; 1,000,000-point viewport |
| [Panorama and World](#panorama-and-world) | Paid live, including the end-to-end run; desktop on pre-rebase heads | Pending: desktop recheck of the merged lane |
| [Trained models](#trained-models) | Paid live; desktop on pre-rebase heads | Pending: private trained models; desktop recheck of the merged UI |
| [Workflows](#workflows) | Paid desktop step review and uploads; paid live decisions | Passed at UI scale 1.0; pending: UI scale 2.0 |
| [Film](#film) | Paid end-to-end run through local MCP; desktop dialogs | Pending: desktop rerun after #407, #408 and #428 |
| [Previews and playback](#previews-and-playback) | Free live; desktop, including the pager after #423 | Pending: human listening |
| [Library organization](#library-organization) | Free live writes; desktop read-only | Pending: desktop Apply |
| [Composer and IME](#composer-and-ime) | Desktop on 5.0.1, 5.1.2 and 5.2.1; paid job strip and card | Pending: UI scale 2.0 of the strip; IME by a person |
| [MCP parity](#mcp-parity) | Free and paid live through local MCP, including the end-to-end run | Passed for the tools on `ff8d29d8`; pending: later tools on merged heads; #427 and #429 open |

### Image

- **Installed and hosted CI:** shared quotes, durable submission, uploads and
  recovery run in every suite above. Saved image application decoded and packed
  a representative output on 5.0.1, 5.1.2 and 5.2.1 (see the
  [earlier candidate](#earlier-099-candidate-and-decision)).
- **Desktop and free live:** on the 0.10.0 build from #70, Blender 5.2.1 LTS,
  a typed API key and secret, the connection test, the environment credential
  source and a log scan for credential values passed. GPT Image 2 had an exact
  quote equal to local MCP `estimate_cost` with the same parameters. A wrong
  secret or unknown project then showed only *HTTP 403*; #352 later added
  guidance, not rechecked on a desktop.
- **Paid live:** the authorized [hosted smoke run](../MAINTAINERS.md#smoke-lane)
  produced a `READY` image job with receipt-verified files on 2026-10-09.
  [Render Image](#render-image-and-render-video) adds GPT Image 2 jobs with a
  captured scene reference.
- **Status:** passed. A paid job started from the composer is tracked under
  [Composer and IME](#composer-and-ime).

### Material

- **Installed:** a representative material's five PBR maps decoded, packed and
  were assigned to a captured mesh slot on 5.0.1, 5.1.2 and 5.2.1 after #340.
  #394 keeps material maps out of World candidates; desktop passes on builds
  before #394 had offered them.
- **Free live:** exact PATINA Material quote with UI/MCP parity, and previews of
  an existing texture set.
- **Paid live:** the hosted smoke material job reached `READY` with
  receipt-verified maps.
- **Status:** passed. No desktop application of a newly generated material is
  recorded.

### Render Image and Render Video

- **Installed and hosted CI:** #377 and #379 pass installed suites on 5.0.1,
  5.1.2 and 5.2.1. #387, #389, #392 and #393 keep captured origins across form
  loads, price only the selected scene, treat undeclared conditional inputs as
  never defined and stop captures from invalidating their own uploads.
- **Paid live, 2026-10-10:** local MCP `generate` over native forms prepared in a
  script-driven Blender 5.1.2 window on macOS arm64 (not physical input), on
  pre-merge builds that included #383 and #393:
  - Render Image, GPT Image 2 with a camera still: two jobs, both ready, with
    receipt-verified PNGs.
  - Render Video, Seedance 2.0 Fast, 480p, 4 s, with a saved image as the first
    frame. Sent as `image` beside the scene clip, the job failed on the service
    within seconds because the model refuses that combination, and was
    reimbursed. Sent as image 1 of the reference images (#377, #379), the rerun
    completed; its MP4 was receipt-verified and inserted as a Sequencer strip.
    The merged #379 head differs from the tested one.
  - Minimax H3 was quoted with the real clip and not submitted.
- **Desktop (pre-merge #377 and #379 heads, read-only):** **Use as video first
  frame** in sidebar and Studio Jobs; confirmations for Minimax H3, Seedance 2.0
  Fast, Kling V3 Omni Video and Kling O1 Reference Video; the reference-image
  routing lines; binding, removal and refusal of a second handoff; Esc and
  focus; one undo step with redo. Those builds did not capture the scene clip.
- **Desktop, paid pass:** a saved GPT Image 2 result handed off as the first
  frame of Minimax H3, the Render Video default; **Capture and upload scene**
  captured and uploaded the clip; the free quote became ready, and the request
  built for it sends the frame as reference image 1 and the clip in the reference
  videos, with no separate image field. The quote was not submitted.
- **Service:** Seedance 2.0 Mini's first-frame exclusivity is a known
  service-side issue, already reported to the Scenario backend team. No
  Seedance 2.0 Mini job was submitted.
- **Status:** passed. The clip capture and quote ran at UI scale 1.0 on Blender
  5.1.2 only, and no Minimax H3 or Wan 3.0 job has run.

### Audio

- **Installed and hosted CI:** #360, #375 and #412. A representative MP3 became
  a sound strip on 5.0.1, 5.1.2 and 5.2.1 with the earlier candidate.
- **Free live:** exact Google Lyria 3 Pro quote with its one-of input
  requirement and UI/MCP parity; an offline waveform envelope of an existing
  ElevenLabs Sound Effects v2 result.
- **Paid live:** the hosted smoke audio job reached `READY`.
- **Desktop:** with the 0.10.0 build from #70 on Blender 5.2.1 LTS, 591 s of
  offline Sequencer playback of the hosted smoke video and MP3 ran at 22.9 to
  25.0 fps with the extension enabled and no errors; the preview area stayed
  black because of a fixture issue. Pre-merge #418 heads drew a waveform at UI
  scales 1.0 and 2.0.
- **Human:** the maintainer accepted the sound quality of the reviewed outputs
  on 2026-10-09.
- **Status:** pending. Listening through the new **Play** controls (#418) is a
  human check for the maintainer under #189 and #68; Play audio was not clicked
  because the test machine's default handler adds files to a personal media
  library.

### 3D generation and imports

- **Installed and hosted CI:** #362 (Edit 3D pricing), #366 (package
  classification), #402 (undo step for imports) and #413 (OBJ, FBX, glTF and
  PLY import).
- **Free live:** exact Rodin Gen-2.5 Text to 3D quote with UI/MCP parity. Two
  existing Meshy 7 text-to-3D results, each a GLB with an alternate OBJ, MTL and
  four PBR maps, were classified and imported through local MCP in background
  Blender 5.1.2: one root object per import in a new collection, the selection
  kept, and matching GLB and OBJ extents.
- **Desktop (pre-merge #413 heads, read-only):** GLB and alternate OBJ imports;
  OBJ map color spaces; the OBJ normal-strength fix that #413 merged. The tested
  builds lacked #402, so an import had no undo step of its own and left the file
  unmodified; desktop Undo and the save prompt after #402 are not rechecked.
- **Desktop, paid pass:** Tencent UV Unwrapping from an uploaded mesh snapshot
  returned an FBX primary result with OBJ alternates. **Apply** opened a card
  with a paged preview row and the FBX and OBJ imports; the FBX review and its
  import into a new group passed, with the selection unchanged. A first attempt
  failed on the service and showed no reason in the extension, which #425
  addresses.
- **Paid live:** the hosted smoke 3D job reached `READY`. Meshy 7's and Tencent
  UV Unwrapping's packages have been imported from live results; no catalog
  model was found producing JSON glTF.
- **Status:** pending. No mesh PLY import of a real result has run, and no
  catalog model produces JSON glTF. Owner: the maintainer, under #65 and #68.

### Splats

- **Installed and hosted CI:** #414 (point-cloud import) passes installed
  suites on 5.0.1, 5.1.2 and 5.2.1; #356 (bounded decoders) on 5.1.2 and in
  hosted CI.
- **Desktop, paid pass:** TripoSplat from an uploaded image returned one SPZ.
  Its import review and import as a coloured point cloud of 262,144 points
  passed, upright with the default axes and with the selection unchanged.
  TripoSplat returned no PLY, and the only PLY splat producer found was over
  the pass's per-job budget.
- **Status:** pending: PLY splat generation and import, and a 1,000,000-point
  viewport check. Owner: the maintainer, under #65 and #68.

### Panorama and World

- **Installed and hosted CI:** #363, #367 (on 5.0.1, 5.1.2 and 5.2.1), #391,
  #394 and #415. On 2026-10-12 #416 merged as `1741a1e1`, adding the native
  Environment lane, and #417 as `881a9347`, adding panorama contract smoke cases
  and an advisory report.
- **Paid live, 2026-10-10:** local MCP in background Blender 5.1.2 on pre-merge
  builds. Flux 360 returned a 1536 x 768 equirectangular PNG. HDRi Skybox from
  that result returned an EXR original and an LDR JPEG, both receipt-verified;
  see the [World format limits](../KNOWN_LIMITATIONS.md#creation-and-scene-application).
  A 2x skybox upscale completed on the service, but its default download was a
  transformed JPEG that failed verification. #391 downloads untransformed
  originals, and resuming that saved job without a new submission then verified
  a 3072 x 1536 PNG. World application and restore of the PNG and EXR matched
  the baseline exactly. HY World was quoted, not run.
- **Paid live, end-to-end run:** a Skybox GPT panorama applied as World and
  converted to an HDRI through local MCP on `3720c9e3`.
- **Desktop (pre-rebase #415 to #417 heads):** the Environment tab and modes in
  the sidebar and Studio, verified-model lists, settings, the upscale cap, 17
  free quotes, World application of PNG, OpenEXR and JPEG panoramas with
  restore, Esc and focus. World application adds no undo step, as documented.
- **Status:** pending: a desktop recheck of the merged lane, including the
  rebased composer tab row, which postdates the desktop pass; a local panorama
  upload and From image beyond its quote need a session without the desktop
  spend guard. Owner: #98 and #66. Seam, pole and
  dynamic-range measurements remain advisory.

### Trained models

- **Installed and hosted CI:** #357, #363, #371, #374 and #376 are merged, and
  #409 merged on 2026-10-12 as `6a6b4c75`: the model picker's trained LoRAs and
  compositions. On 2026-10-13 #410 merged as `3111664b`, adding strengths and
  project defaults, and #411 as `df2fac37`, adding MCP trained models and
  defaults.
- **Free live:** on a pre-merge #411 head through local MCP in background
  Blender 5.1.2: public trained models listed, exact quotes equal to the #374
  contracts, byte-identical form and MCP payloads, scoped defaults and local
  refusals.
- **Paid live, 2026-10-10:** four jobs from local MCP on that head, FLUX.1 Dev
  with one LoRA, two LoRAs and a composition, and FLUX.2 Dev with a LoRA. All
  completed and were receipt-verified and imported.
- **Desktop (pre-rebase #409 and #410 heads, 23 free quotes):** the picker with
  public LoRAs and compositions, search, base choice, stacking, strength edits,
  per-project default Save, Use, Clear and Replace, one fresh quote per change,
  Esc and focus. #409 fixes four findings from that pass and #410 the strength
  that Backspace reset to 0.0, without a desktop recheck. With
  #410 a LoRA starts at the model's declared strength or, without one, at 0.75,
  the Scenario web app default; the tested build predates that rule.
- **Status:** pending. Private LoRAs and compositions need credentials that own
  them: a human check for the maintainer under #97. Restart persistence and a
  desktop recheck of the merged picker, strengths and defaults also remain, and
  #411's tools ran live only on a pre-merge head.

### Workflows

- **Installed and hosted CI:** #354, #368, #383, #385 and #395 are merged, and
  on 2026-10-12 #403 (`ae791f5c`, step decisions through shared jobs), #404
  (`96e5dfa3`, MCP `workflow_job_steps` and `decide_workflow_step`), #405
  (`5a175b2c`, step review in Studio and Jobs) and #406 (`c90955dd`, private
  review previews) merged.
- **Free live:** a local file uploaded into a public workflow's input (one part,
  imported, receipt-verified), pricing held while uploading, and **Use saved
  upload** reuse that discards the earlier quote.
- **Paid live, 2026-10-10:** private test workflows with approval and selection
  steps, created through the documented API and deleted afterwards, since no
  public workflow has such steps. Approval through the native operator and
  local MCP passed. **Stop workflow** canceled the job and only the step that had
  run was charged. A text selection reached its next step. A selection feeding
  a ForEach loop was sent although its step links could not be read, and the
  charge exceeded the one-pass quote. #395 now warns about loop quotes, and
  the merged #403 to #405 refuse such selections. These decisions ran on
  pre-fix heads of #403 to #405; the merged code has no paid recheck.
- **Desktop (pre-rebase heads):** the workflow picker, input form, Library
  reference, Generate confirmation and, on #395's head, the loop-cost warning.
- **Desktop, paid pass:** a local file and viewport and camera captures were
  uploaded into workflow inputs, each after its own confirmation and without
  generating. A public ForEach workflow's dry-run price showed the loop-cost
  warning in the form and the confirmation; a workflow without a loop did not.
  A private test workflow with a selection and three approvals, created through
  the documented API and deleted afterwards, ran once. The review dialog loaded
  the candidates' previews, Esc closed it without sending, two of three
  candidates were chosen and an approval was sent. A decision sent from a dialog
  after its step was decided elsewhere was refused with *The workflow step
  changed; review it again*, and **Stop workflow** at the last approval canceled
  the job with only the step that had run charged.
- **Status:** passed at UI scale 1.0 on one private test workflow. The review
  dialogs at UI scale 2.0, concurrent decisions and rejection inside a loop
  remain. Owner: #65 and #66.

### Film

- **Installed and hosted CI:** #361, #364 and #407 are merged, and #408 merged on
  2026-10-12 as `fc8b2231` after its Windows hosted jobs passed: the portable
  case-study bundle. On 2026-10-13 #426 merged as `0aa86d74`, finding `ffmpeg`
  and `ffprobe` in standard install folders when Blender is started from the
  Dock, and #428 as `3556dfba`, explaining why a Film review cannot gather its
  sources and warning when a loaded recipe declares none.
- **Desktop (pre-fix #407 and #408 heads):** the Film panel, recipe loading, the
  saved upload picker, review preparation, discard and invalidation, building the
  review scene, the export file browser and render confirmation passed. Every
  native export and case-study approval was refused as a scene change, because
  the export's own view-layer synchronization counted as an edit. The same
  commands in background Blender wrote a valid 1920 x 1080, 24 fps H.264 MP4
  and a complete bundle that reopened offline. #407 fixes the synchronization
  with an installed reproduction.
- **Paid live:** the [end-to-end production run](#end-to-end-production-run)
  built previz and final reviews through local MCP, exported a 20 s 1080p MP4
  with audio and saved a case-study bundle, after working around the two
  defects that #426 and #428 later fixed. Its media came from uploads; no Film
  model task ran.
- **Status:** pending: a desktop rerun of export, cancel, Open folder, Copy
  SHA-256 and the case-study save after #407, #408 and #428, since the fixes
  landed after the pass, and human playback review. Film cannot capture or
  export an artist-built multi-shot scene or take a saved generation result as a
  task source; see the
  [known limitations](../KNOWN_LIMITATIONS.md#runtime-and-authentication).
  Owner: #66 and #68. Film stays experimental.

### Previews and playback

- **Installed and hosted CI:** #359, #360, #375, #384 and #412 are merged, and on
  2026-10-12 #418 (`ee7586fb`, Play, Play in Blender and Waveform for saved
  video and audio), #419 (`fa711174`, automatic result previews with a pager
  for more than four results) and #420 (`2e89cae8`, MCP
  `inspect_result_previews`) merged. #422 (`fd9fd0f1`) moved the folder and
  link buttons onto Play's launcher; they have native tests with a recorded
  launcher and no physical desktop check.
- **Free live (background Blender 5.1.2):** server stills and local previews for
  audio, 3D, video, texture-set and image results, MCP inspection matching the
  tiles, the audio envelope, retry, and the pause while online access is off.
- **Desktop (pre-merge #418 and #419 heads, read-only):** tiles in Jobs,
  Generations and Studio; Retry; Play video in the system player; Play in
  Blender; the waveform; status lines wrapped by measured width.
- **Desktop, preview pager (2026-10-13, `main` at `2e89cae8`):** a ZIP built
  from that commit (SHA-256
  `970275023871f1ee643d683ad9b42e913e1d72fc104f34a413ad2fe35c9b5281`) on
  Blender 5.1.2, macOS arm64, at UI scales 1.0 and 2.0, with real mouse and
  keyboard input, Online Access disabled and saved jobs written offline from
  synthetic images, so no service request and no spend. In Jobs, Generations
  and Studio (the Jobs page at both scales, the Results page at 1.0), a job with
  six results paged forward and back, the arrow at each end stayed in place,
  disabled, and a click on it changed nothing, the range line read `1-4 of 6`
  and `3-6 of 6`. A job with four results drew no pager in the sidebar's Jobs
  panel or on the Studio Jobs page. After an arrow click the viewport still
  answered orbit, wheel zoom and keys, and no field took keyboard focus. One
  defect: in the 3D View sidebar at its default width, at both scales, a paged
  row's arrows were about 1.65 times as tall as its tiles, where the
  [UI contract](../UI_STYLE.md#saved-result-previews) makes them as tall as the
  icons, and its tiles were about 30% smaller than those of an unpaged row in
  the same panel. In Studio and in a widened sidebar the arrows matched the
  tiles. #423 (`3720c9e3`) then merged to fit a paged row.
- **Desktop, #423 and #424 recheck:** offline with synthetic saved jobs, at UI
  scales 1.0 and 2.0, a paged row's arrows were as tall as its tiles' icon cells
  in Jobs, Generations and Studio, nothing was clipped, captions kept their
  numbers, real clicks paged forward, clamped at the end and returned, and an
  unpaged row was unchanged. Blender insets each image in its cell, so in the
  default-width sidebar the arrows still reach about 9 px (scale 1.0) or 18 px
  (scale 2.0) beyond the visible image, and paged tiles stay about 30% smaller
  than unpaged ones: a design note, not a defect against the UI contract.
- **Status:** pending: human listening and Play audio (the maintainer, under
  #189 and #68); the waveform and Studio's Results page at UI scale 2.0; and the
  waveform alignment fix proposed on #189.

### Library organization

- **Installed and hosted CI:** #355, #373, #378 and #380.
- **Free live (pre-merge #380 head, background Blender 5.1.2):** local MCP and the
  native operators created a temporary collection, added and removed one asset
  and added and removed tags. Each apply was verified by an independent read,
  and the asset was restored. Repeated, unchanged, discarded and rejected reviews
  and a duplicate collection name were refused without a write.
- **Desktop (read-only, also in a 1018 x 671 pt window):** Library pages, Organize
  dialog focus, Unicode tags and the 30-tag limit, dismissal, Discard, viewport
  shortcuts and, after fixes, the card placement and read-enabled controls.
  Japanese IME did not compose in the Tags field, as in Blender's own fields.
- **Status:** pending: Apply from the desktop dialog. It is a free write, but the
  write-capable desktop session was refused by the agent permission rules.
  Owner: #66.

### Composer and IME

- **Installed and hosted CI:** #353, #358, #362, #365, #369, #397, #398, #401
  and #421, and #424, merged on 2026-10-13 as `dad196a8`, which draws the job
  strip's progress bar to its reported fraction.
- **Desktop on the 0.10.0 build from #70 (offline):** physical journeys on
  Blender 5.0.1, 5.1.2 and 5.2.1 LTS at 2x backing and 5.2.1 LTS at 1x opened
  Studio on the first click from a focused prompt (5 of 5 each), committed
  Unicode and dead-key text and then selected an object. On 5.1.2, wheel zoom,
  N and the header button also worked, and a 1018 x 672 pt window kept the
  composer usable. The card was drawn under an open sidebar there; #353 fixed
  that.
- **Desktop on later heads:** #353 beside the sidebar; #397's real double-clicks
  reset placement and width, and the card stays in view at window edges and
  after resizing (tested on #398's head); #398's F2 field, dead keys and
  composition after a cancelled rename (see the
  [input method limits](../KNOWN_LIMITATIONS.md#interface-and-capture)). A
  refused Generate ended the composer session in that build; #401 fixes it,
  without a desktop recheck.
- **Desktop, paid pass:** real jobs drove the
  [compact job strip](../UI_STYLE.md#compact-job-strip) through Submitting,
  Generating with a percentage, Finalizing, Downloading results, Importing,
  Ready to apply, Applied and Generation failed. **Inspect** opened the job card
  with Esc and viewport focus returning, **Reuse** and **Apply** opened their
  reviews, and the cross dismissed the tray. The determinate progress bar was
  drawn full at every fraction, which #424 fixes. The service never reported a
  queued state, so Waiting was not seen, and Cancel was not offered because no
  job reported `inference`.
- **Desktop, #423 and #424 recheck:** with authorized generation at UI scale
  1.0, the strip and the collapsed pill filled to the reported 3% over a dim
  track, states without a percentage showed only the track, and the idle
  composer drew no bar. After a job is applied, the collapsed pill keeps the
  job's grey done line until the job is dismissed, as documented; whether that
  reads as a full bar is a design question.
- **Status:** pending:
  - The job strip and card at UI scale 2.0, the Waiting state, and Cancel on an
    `inference` job (#65 and #66).
  - IME composition after F2 with an input source a person selects, and the
    candidate window: a human check under #66.
  - #401's endings after an error or a file load, and UI scales 1.25 and 1.5,
    on a desktop (#66).

### MCP parity

- **Installed and hosted CI:** authenticated loopback MCP contracts in every
  suite. #386 returns tool failures without tracebacks or local paths, and #388
  derives history row kinds.
- **Free and paid live through local MCP:** `estimate_cost` equal to the native
  price for Image, Video, 3D, Material and Audio forms; trained-model payloads
  byte-identical to the form; organization; preview inspection matching the
  tiles; World application and restore; Render quotes and generation over
  prepared native forms; workflow approval and rejection. The end-to-end run
  used uploads, model schemas, quotes, generation, waits, result application,
  World, organization and the Film tools on `3720c9e3`.
- **Status:** passed for the tools on `main` at `ff8d29d8` and those the
  end-to-end run used. #404's `workflow_job_steps` and `decide_workflow_step`
  and #411's trained-model tools ran live only on pre-merge heads. The
  end-to-end run found that the first quote of an uncached model fails while its
  description loads (#427) and that local MCP scene changes leave the file
  unmodified (#429); both fixes are open. No third-party MCP client session is
  recorded.

### End-to-end production run

On 2026-10-13 a maintainer-authorized production test drove an exact ZIP built
from `main` at `3720c9e3` through local MCP, in Blender 5.1.2 on macOS arm64.
It is evidence for the shared runtime and its MCP tools, not for desktop
interaction.

- It built a 20 s multi-shot action sequence in Blender: generated character and
  prop images, image-to-3D models imported as GLB, a panorama applied as World
  with an HDRI conversion, a blockout, four cameras with a bullet-time orbit and
  a previz render.
- Seedance 2.5 rendered the final video from a previz segment and reference
  stills. The Film lane assembled it into a 20 s 1080p MP4 with audio and saved
  a case-study bundle.
- Fixed since: Film could not find `ffprobe` and `ffmpeg` in a Blender started
  from the Dock (#426), and a final Film review hid its cause behind a generic
  error (#428).
- Under review: a failed job showed no reason (#425), the first quote of an
  uncached model failed while its description loaded (#427), and local MCP scene
  changes left the file unmodified, so quitting gave no save prompt (#429).
- Feature gaps, now among the
  [known limitations](../KNOWN_LIMITATIONS.md#runtime-and-authentication):
  Film cannot capture or export an artist-built multi-shot scene, Render Video
  cannot use an already-rendered previz video as its motion reference, and Film
  cannot take a saved generation result as a task source, so its case-study
  ledger lacks that cost.

### Pending checks

| Check | Lane | Owner | Reason |
| --- | --- | --- | --- |
| Job strip and job card at UI scale 2.0, the Waiting state and Cancel on an `inference` job | Composer | #65 and #66 | The paid pass ran at UI scale 1.0; no job reported a queued state or `inference` |
| Workflow review dialogs at UI scale 2.0, concurrent decisions and rejection inside a loop | Workflows | #65 and #66 | The paid pass ran at UI scale 1.0 on one private test workflow |
| Render Video handoff and clip capture on Blender 5.0 and 5.2 | Render Video | #66 and #68 | Desktop passes ran on Blender 5.1.2 only |
| PLY splat and mesh PLY imports of real results, and a 1,000,000-point splat viewport | Splats, 3D | Maintainer, #65 and #68 | The only PLY splat producer found was over the pass's per-job budget; no mesh PLY job ran |
| Failed-job reasons, MCP quotes of uncached models, and the file marked modified after local MCP changes | Jobs, MCP | #65 and #68 | #425, #427 and #429 are open |
| IME composition after F2 with a person-selected input source | Composer | Maintainer, #66 | Human check |
| Listening through Play and the system player | Audio, previews | Maintainer, #189 and #68 | Human check |
| Private LoRAs and compositions | Trained models | Maintainer, #97 | Human check; the test credentials own none |
| Trained-model picker, strengths and project defaults on merged heads | Trained models | #97 | #409's and #410's fixes merged after the desktop pass |
| Desktop export and case-study save after #407, #408 and #428 | Film | #66 and #68 | The fixes landed after the desktop pass; the end-to-end run used local MCP |
| Library Apply from the dialog | Library | #66 | Write-capable desktop session refused by the agent permission rules |
| Merged Environment lane, its rebased tab row, local panorama upload and From image | Panorama | #98 and #66 | #416 merged after the desktop pass; uploads need the spend guard off |
| Folder and link buttons on the shared launcher | Previews, Film | #68 | #422 has native tests only; no physical check of the buttons |
| `workflow_job_steps`, `decide_workflow_step` and #411's trained-model tools on merged heads | MCP | #65 and #68 | Their live evidence ran on pre-merge heads |
| #401 session endings and #402 import Undo and save prompt | Composer, 3D | #66 and #68 | Fixes merged after the desktop passes |
| Weekly macOS and Windows rerun | Platforms | #399 and #400 | Stale expectation corrected by #396 |
| First scheduled monthly paid smoke run | CI | #40 | Not run yet |
| Final candidate installed suite, hosted CI, update and restart | All | #68 | TODO(final candidate) |
| Release ZIP, checksums, attestations, extension index and HTTPS install | Release | #36 and #68 | After publication |

### Service behavior observed live

- Dry runs check declared conditional requirements but not exclusivity stated
  only in input descriptions; the service refuses such a job after accepting
  it.
- A pending upload's retrieval omitted the part plan, so uploads stopped before
  sending bytes until #383 used the plan from the create response. The SDK
  offers no way to abort an upload.
- Upscaled skybox results serve a transformed image at their default URL; the
  untransformed original needs `originalAssets`.
- A retrieved workflow job omits step links on several node types, so the
  extension cannot always tell which steps feed a loop.
- A wrong secret and an unknown project both return HTTP 403.
- In the paid desktop pass no job reported a queued state; jobs went from
  submission straight to generating. GPT Image 2 reported only 3%, while
  TripoSplat and Tencent UV Unwrapping reported several intermediate fractions.
- A failed job carries its reason in the job's metadata, which the extension
  does not show yet (#425).
- A 20 s Seedance 2.5 1080p take failed on the service after about 32 minutes as
  taking too long; takes of 13 s and 7 s succeeded. Their progress stayed near
  91% for most of each run.

## Earlier 0.9.9 candidate and decision

Reviewed on 2026-10-09 after the implementation stack merged. The supported
release remains held by #68. The current development candidate includes the
[grayscale material fix, #340](https://github.com/scenario-labs/blender-plugin/pull/340).
That fix and its acceptance record (#341) are merged into `main` at
`88b6b3ec8ebd5707581f6d39f0fd158c784873a2`. The exact tested source and ZIP
identities below remain unchanged; the merge does not certify a rebuilt archive.

| Item | Identity |
| --- | --- |
| Merged main baseline | `6c70d2edb385f6bd9f4a5e53c1eee66c575ebd16` |
| Corrected candidate source | `e73c700b4fb288acf8956615c40e085c7ee068b5` |
| Package | `scenario-0.9.9.zip`; development version unchanged |
| SHA-256 | `bc241cace5fe1d8158cc00cdc54c1a12c10eaddcafc954c3c1172bafd196494f` |
| Source and bundle | All 140 packaged Python sources match; locked SDK 2.2.0 bundle, package GPL and dependency notices validate |

The locked unit suite passes **3,927 tests**, with the existing SDK explicit-bearer
precedence expected failure. Changed-file Ruff and knowledge structure checks
pass; unrelated source-freshness warnings remain. This does not resolve the SDK
authentication gap or establish fresh live onboarding.

The same corrected ZIP passes the full installed suite in isolated macOS 27.0.1
arm64 profiles:

| Blender | Bundled Python | Installed suite | Native update and offline restart |
| --- | --- | --- | --- |
| 5.0.1 | 3.11.13 | 1,147 passed, two Windows-only skips | Pass |
| 5.1.2 | 3.13.9 | 1,147 passed, two Windows-only skips | Pass |
| 5.2.1 LTS | 3.13.13 | 1,147 passed, two Windows-only skips | Pass |

All three update runs use synthetic predecessor SHA-256
`2201ef15431ea764be17adfb270c2e1dbd4f5a1706651aff038cebd7e211b4bd`.
Only its version declarations differ from the candidate. Project selection,
scoped jobs/results/uploads, nonempty Film state, workflow references and the
scene survive native update and offline restart. Each report records zero
service requests, a stopped loopback server, removed successful profiles and an
unchanged normal profile. This is synthetic lifecycle acceptance, not a published
release pair or public HTTPS delivery.

Existing local representative outputs were matched to their saved byte counts
and SHA-256 receipts, then exercised through the installed candidate's native
application primitives on all three Blender versions:

- Image: decoded and packed successfully.
- Material: five PBR maps decoded, packed and assigned to the captured mesh slot;
  the base preview stays unused and the old material remains intact.
- GLB: one mesh with 56,602 vertices imported; prior selection was preserved.
- Video and audio: independent verified snapshots became movie/sound strips at
  the requested frame without changing scene timing. Blender's decoded MP3 strip
  duration differs by one frame between the tested versions; no duration is
  forced or claimed to be sample-exact across decoders.

These are native primitive checks using existing outputs, not a new service
submission, coordinator approval journey or physical desktop interaction.
The maintainer separately accepted motion/playback and sound quality for the
reviewed video/audio outputs on 2026-10-09. This does not establish sustained
candidate GPU/audio playback or quality across every provider/model.

### Failure found and corrected

The merged-main ZIP SHA-256
`c01562d338e54dcd0cdd6b604afac21c2afc7ed52b8df3c33827e7335db1bdaa`
passed 3,918 unit tests with the same expected failure, 1,146 installed tests
plus two skips per supported macOS Blender version, and synthetic update/restart.
However, applying the representative material failed on all three versions:
its scalar maps were valid grayscale PNGs, which general image preflight rejected.
#340 admits 8-/16-bit grayscale images while preserving panorama formats and all
receipt/resource checks. The original material now applies, and new synthetic
regressions cover both bit depths without storing private outputs in the repository.
Do not use the initial merged-main ZIP as the accepted material candidate.

[Hosted main CI](https://github.com/scenario-labs/blender-plugin/actions/runs/37939493112)
is green for the merged baseline, including Linux/Windows Blender 5.0.1, 5.1.2
and 5.2.1. Those jobs build separate archives and do not certify #340 or this
macOS ZIP. Their later merges do not change the identity of the tested archive.

### Remaining acceptance handoff

The merged-main exact-ZIP desktop session launched in the isolated review app
and exited cleanly with its normal profile unchanged. The computer-control
service failed at native-pipe startup, including after a reset, before any
interaction or screenshot could be verified. This is a tool attachment failure,
not evidence that Blender crashed or that UI checks passed. The corrected ZIP
has no new physical desktop evidence. Earlier desktop evidence below retains
its own artifact identity.

This handoff dates from 2026-10-09; the
[0.10.0 evidence by lane](#0100-evidence-by-lane) supersedes it where it records
newer evidence. Complete these checks on the corrected candidate before releasing:

1. Fresh API-key onboarding from the documented instructions: connection success,
   offline/permission errors, explicit credential source and optional project
   selection. Changed credentials/projects must clear quotes and isolate results.
2. Compact capture, upload, exact estimate, approved generation, inspect and apply;
   Studio/Library reference reuse must invalidate the old quote and preserve the
   selected destination. Existing results can cover recovery/application; a new
   paid journey requires a fresh explicit project and quote/budget approval.
3. Candidate-level UI/MCP approval parity, cancellation, restart/uncertain states,
   failed transfer/import and scene/file/project switching. The installed suites
   cover synthetic cases; record the corresponding integrated native journey.
4. Physical focus/text/IME, viewport, small-window and alternate-DPI checks in
   each claimed desktop environment; sustained candidate rendering/playback and
   audio stability. Preserve the separate accepted human media review above.
5. Complete reference-upload acceptance and retain explicit
   experimental/unavailable capability limits. The 2026-10-09 administration
   follow-up added and read back required `ci-ok` while preserving all other
   protections (#45), and configured the protected `smoke` environment (#40).
   The authorized five-lane hosted run and decrypted completed-result recovery
   passed. Its version-1 plan has no new reference uploads. Scheduled runs now
   use the committed monthly plan with a fixed 40 CU cap; none has run yet. See
   the [maintainer record](../MAINTAINERS.md#smoke-lane) for hosted-run evidence
   and the remaining scope.
6. Validate the actual release-please 0.10.0 artifact, then complete the published
   checksum/provenance, extension index and native HTTPS installation checks at
   their proper release stage. This 0.9.9 candidate is not a published release.

The merged legacy OBJ/MTL recovery fix removes production metadata repair as a
prerequisite for existing downloads. These acceptance checks neither regenerate
those assets nor require a production backfill. Film, direct workflow uploads,
interactive nodes/general workflow cancellation and asset organization retain
their documented limitations; this record does not declare those scopes complete.

## Historical candidate identity

Initial candidate reviewed on 2026-10-07; later evidence is identified separately below:

| Item | Identity |
| --- | --- |
| Source | `42bd9e48c32f8bbc62e1fa9792ac939b9c578b51` |
| Integration | Stack #314 through #309, followed by [#315](https://github.com/scenario-labs/blender-plugin/pull/315) and [#316](https://github.com/scenario-labs/blender-plugin/pull/316) |
| Package | `scenario-0.9.9.zip`; development version unchanged |
| SHA-256 | `44d4a61354c8f91e2fe93e93e6834259216787ee1403562308de322d27844b42` |
| Bundle | Locked Scenario SDK 2.2.0 dependencies; installed bytes verified |
| Source comparison | All 159 packaged source files match the candidate checkout |

The eventual release-please 0.10.0 ZIP will have different bytes. Repeat candidate
validation for that artifact and record its checksum and revision here; this
record cannot certify an unbuilt release. Rebuilding the same source does not
justify substituting a different archive without checking it.

## Historical verified evidence

The locked offline unit suite passes **3,807 tests**, with the existing SDK
explicit-bearer authentication expected failure still unresolved. It is not
production authentication acceptance.

The same candidate ZIP passes **1,058 installed tests per version** on macOS
27.0.1 arm64:

| Blender | Bundled Python | Installed suite | Native update and offline restart |
| --- | --- | --- | --- |
| 5.0.1 | 3.11.13 | Pass | Pass |
| 5.1.2 | 3.13.9 | Pass | Pass |
| 5.2.1 LTS | 3.13.13 | Pass | Pass |

Installed runs use `tools/test_blender.py --suite all`, with `--zip` reusing the
same archive on subsequent versions. These runs verify installed source and
bundle bytes, block external test traffic and preserve the normal user profile.
They exercise synthetic service responses; they do not establish provider
compatibility or physical desktop interaction.

Native lifecycle checks use `tools/test_repository_update.py --candidate-zip
<archive> --test-predecessor`, following the
[package update procedure](../development/validation.md#scenario-package-state-across-updates).
The synthetic predecessor has version `0.0.0` and SHA-256
`49bc40b8f175c5dba539c8898b6f1c90c09d6742dcc0f8111e294adf703add70`.
Only the predecessor's version declarations differ from the candidate. All three
runs install and update through Blender's loopback repository, verify exact
archive bytes and enabled state, then reopen the saved blend offline.
The fixture's preferences, scoped jobs, uploads, verified result bytes,
application claims, captured-mesh bindings, Film task/upload associations and
scene survive. Each report records zero service requests, normal-profile
preservation, server shutdown and disposable-profile cleanup. This is synthetic
lifecycle evidence, not compatibility between published releases or public
HTTPS update delivery. The probe does not seed a nonempty project preference.

[Hosted CI for the preceding #315 head](https://github.com/scenario-labs/blender-plugin/actions/runs/37691216091)
passes `ci-ok`, including Python 3.11/3.13 and Linux/Windows Blender 5.0.1,
5.1.2 and 5.2.1. Those jobs build their own archives; their results do not prove
the macOS archive above on other platforms. Check the current PR head after
restacking; a prior green run cannot certify a later change.

Non-submitting live metadata/estimate requests succeeded for Image, Materials,
Video, 3D and Audio using one private suite in the configured test key's default
scope. All five case reports contain zero saved jobs, and no submission-attempt
marker exists. No paid generation, live upload/result round trip or project-override permission journey
is included in this record. Quote values and private service evidence are not
published here.

## Later project-scope evidence

Reviewed on 2026-10-08: [#316](https://github.com/scenario-labs/blender-plugin/pull/316)
is merged as `27bfb023b4cb90a06a0db0bdc8803038ae9145ee`.
Its later checks cover distinct archives and do not replace the initial
candidate's synthetic update/restart evidence above.

- Native mouse/keyboard and inspected screenshots pass on macOS 27.0.1 arm64,
  Blender 5.1.2, source `29de2245b22e64bde6f1713797fd40d3eeb844c9`, ZIP SHA-256
  `3bd0a4b03ec9afe792e9bc36ed8805f1c5df06c38dccc46d5e98bdea2d831764`.
  Synthetic fixtures verify project/default saved-job selection, Enter/Tab/Escape,
  focus, whitespace normalization, invalid-ID rejection, environment credentials
  and viewport interaction. The normal profile and installed bytes are unchanged;
  no Python socket connection/bind attempts occur. See the
  [screenshots and limits](../UI_STYLE.md#project-scope-in-preferences).
- The final runtime source `cec73ad75e5b5315db8db91fc340d2f5e1353317` passes
  **3,856 unit tests**, with the existing SDK authentication expected failure,
  and **1,067 installed tests per version** on macOS arm64 Blender 5.0.1, 5.1.2
  and 5.2.1 (two Windows-only skips each). All three runs use ZIP SHA-256
  `bb4b7765050cf8ded9c7f6da1e5cac12e0ab7b0722bc3c5e627522aa971f8c74`.
  Native regressions cover retained local catalog errors, stopped idle retries
  and recovery after correcting project or environment credentials.
  [Hosted CI for this head](https://github.com/scenario-labs/blender-plugin/actions/runs/37833758649)
  also passes; its jobs build their own archives.

The desktop check was not repeated for the final runtime archive. Neither later
archive has a new native update/restart result in this record. These checks do
not establish live project permissions, other OS/DPI desktop acceptance, paid
results or integrated release acceptance.

## Prototype job retirement candidate

The earlier retirement candidate, reviewed on 2026-10-07, has source
`412e504a81721ded9369c7bedd887913e6bb8c92` and ZIP SHA-256
`f4376ab6616e3dbfa59138416379fae9b58ed5663e2f6f53e226b6ac2b3b1fbb`.
It combines stack #314 through #309 at
`cb99a289ad2cf12242f4cbff49237ef36538f225`, the earlier #315–#318 layers
and retirement of the unscoped prototype job engine. Later parent fixes are
outside that exact source identity; this archive does not replace the distinct
project-scope archives above or certify the rebased retirement branch.

That source passes **3,839 unit tests**, with the known SDK authentication
expected failure. All 159 packaged source files match. The same ZIP passes
**1,051 installed tests per version** on macOS 27.0.1 arm64, with two
Windows-only skips, using Blender 5.0.1 / Python 3.11.13,
5.1.2 / Python 3.13.9 and 5.2.1 / Python 3.13.13.
The lower native count reflects replacement of obsolete prototype-engine tests
with read-only startup/pump, local MCP snapshot and unbound-result checks.
Shared SDK submission, uncertainty, transfer and deferred-wait coverage remains.

Same-archive native install/update and offline restart pass on all three
versions using synthetic predecessor SHA-256
`ca6ffddc82a8a59d523255db76a27534973db6e6b15c8951fc4467ebcfa9f090`.
The scoped state and scene survive, with zero service requests, unchanged normal
profiles, stopped loopback servers and cleaned disposable profiles. This is
synthetic lifecycle evidence, not a published release-pair, physical desktop
or live-provider check.
[Hosted CI for its preceding #318 head](https://github.com/scenario-labs/blender-plugin/actions/runs/37695088983)
passed for its own source and separately built Linux/Windows archives.

## SDK service retirement candidate

The earlier service-retirement candidate, reviewed on 2026-10-07, has source
`3105bb9ff0c7a01926faef3cf43640fa23356ea8` and ZIP SHA-256
`8d6c57231e35df5fe4349616875efe612de9039720d7b3df11eb014d872e915a`.
It combines stack #314 through #309 at
`cb99a289ad2cf12242f4cbff49237ef36538f225`, the earlier #315–#319 layers
and removal of the unused prototype service clients. Later parent fixes and
the rebased branch are outside this exact source identity.

That source passes **3,776 unit tests**, with the known SDK authentication
expected failure. All 155 packaged source files match; the five retired
service modules are absent. The same ZIP passes **1,051 installed tests per
version** on macOS 27.0.1 arm64, with two Windows-only skips, using Blender
5.0.1 / Python 3.11.13, 5.1.2 / Python 3.13.9 and 5.2.1 / Python 3.13.13.
The lower unit count reflects retirement of obsolete client tests; shared SDK,
complete-text, upload, scope, transfer and recovery coverage remains.

Native update/restart passes on all three versions from the preceding #319
archive `f4376ab6616e3dbfa59138416379fae9b58ed5663e2f6f53e226b6ac2b3b1fbb`.
The runner's `fixture_predecessor` helper changes only its two version
declarations to `0.0.0`, producing synthetic predecessor SHA-256
`ca6ffddc82a8a59d523255db76a27534973db6e6b15c8951fc4467ebcfa9f090`.
Exact installed-file comparison verifies removal of the old service modules.
Enabled state, scoped saved state and scene survive, with zero service requests,
unchanged normal profiles, stopped servers and cleaned disposable profiles.
This is synthetic lifecycle evidence, not a published release-pair, physical
desktop or live-provider check.
The extended project-aware probe also passes this exact archive/predecessor pair
on all three macOS Blender versions above. It seeds a nonempty saved Project ID,
checks the installed runtime selects that scope before/after upgrade and after
offline restart, and verifies the same key in default/alternate project scopes
cannot read its jobs, uploads or Film upload association. The other credential
fixture uses the same project, preserving the independent credential-isolation
check. All six selected jobs, the other credential job, four uploads and nonempty
Film association survive; both reports require `project_scope_preserved: true`.
These runs again record zero service requests, unchanged normal profiles,
stopped servers and removed disposable profiles. This verifies saved preference
reload and local isolation, not native text entry or live project permissions.

[Hosted CI for #320 head `3ae726b`](https://github.com/scenario-labs/blender-plugin/actions/runs/37697911675)
passed `ci-ok`, including Python 3.11/3.13 and Linux/Windows Blender 5.0.1,
5.1.2 and 5.2.1, for its own source and separately built archives.

## Workflow-reference update validation slice

An earlier integrated source `8197cbb16599a9c9b1ecad010947e63da635a50f`
produced ZIP SHA-256
`449a737bdd7a0d97c1190ccd6e6ee654cb4de3c1baa2036fca86e9969fd5b9d5`.
It includes the Film cleanup fix and release layers through the earlier #329
candidate. All 140 packaged Python sources matched that checkout. Its locked
unit suite passed 3,832 tests with the known SDK authentication expected failure;
the focused update runner suite passed 29 tests. Its installed suite ran 1,131
tests on each macOS 27.0.1 arm64 Blender 5.0.1, 5.1.2 and 5.2.1, comprising
1,129 passes and two Windows-only skips per run.

Native update and offline restart passed on those three versions using synthetic
predecessor `e863e7bc27b2a978ed41b4464d7b6cd41a67201be829ca57635751937c2ac406`,
derived from #329 ZIP
`eaec050ff2c5ba67a25ac55ee9fb9eefb1e546cec7fe0cc6ea632c5a87c74d5d`
by changing only its two version declarations. The probe preserves the complete
workflow schema/form, Unicode prompt and single/array Library references and
bindings, alongside existing jobs, uploads, captured-mesh provenance, Film state
and scene. Other credentials and default/alternate projects cannot use the marked
references. Both update and restart reports require
`workflow_references_preserved: true` when the predecessor seeds a workflow.

A separate Blender 5.1.2 run with older predecessor
`ca6ffddc82a8a59d523255db76a27534973db6e6b15c8951fc4467ebcfa9f090`
passed existing state checks but recorded `workflow_references_preserved: false`
because it has no workflow properties. All runs recorded zero service requests,
stopped servers, removed successful profiles and unchanged normal profiles.
These are synthetic package pairs, not published-release/public HTTPS evidence.
Later sources and archives need their own validation; this evidence supplies no
physical input, live provider journey, spending or complete release acceptance.

## Workflow command validation slice

The workflow command layer above #323 uses a separate exact development ZIP:
SHA-256 `30b2aa7f7448805beec2910435b9ee9fd33c04982c1ebb0b92731488aaf8d089`.
All 135 packaged Python sources match that layer. It passes 1,067 installed tests
on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, with two Windows-specific
skips per run, and 3,801 offline unit tests with the same known SDK authentication
expected failure. The sixteen workflow regressions cover catalog paging, absent/null/empty input definitions,
exact approval, operation isolation, changed price/input/scene/project, failed
persistence, lost-response uncertainty, discard and read-only restart recovery.
Service responses are synthetic and no paid requests or live uploads were made.

These results validate the new MCP command entry points and shared lifecycle;
they do not replace the preceding candidate's update evidence or establish a
completed Studio view, live workflow acceptance or a release-ready 0.10.0 ZIP.

## Expanded Studio validation slice

The explicit native Studio view above #324 uses ZIP SHA-256
`28af5535b3f3755391c7009f29ccdb0c2e47265be4f0ef606fdd09ec6a7984d9`.
All 136 packaged Python sources match that layer. It passes 1,076 installed tests
on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, with two Windows-specific
skips per run, and 3,801 offline unit tests with the known SDK authentication
expected failure. Nine Studio regressions cover unsaved navigation, shared
forms/quotes, continued admitted work, guarded focused-prompt transfer, scene
ownership, requested width and native popup invocation. Mocked layout calls and
direct property assignments do not prove physical interaction or visual layout.

A desktop attempt used the preceding Studio archive
`aa82cd233a1f2be2830b47292c562fad43411ae5dc1a1b60ce6e1461d27a0eaf`.
The isolated application launched, but computer control returned
`cgWindowNotFound` before input or screenshots. The fixture exited cleanly,
removed its disposable profile and preserved the normal profile, with no external
requests. The later Studio checks below provide scoped native interaction proof;
broader acceptance remains required by the [UI guide](../UI_STYLE.md). Workflow/library forms and complete
retained-capability acceptance remain open; these tests do not establish a
release-ready candidate or replace earlier update evidence.

The current candidate rebased onto merged #324 adds a regression and fix for
composer blur consuming the first Studio header click. Its exact ZIP is
`32d81f8cbbc59023dcac10d71c1e87fc70a04265c8791e373639cef53c97c253`.
This identical ZIP passes 1,086 installed tests (two Windows-only skips) on
each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. All 136 packaged Python
sources match the candidate. The full locked unit suite passes 3,852 tests with
the known SDK authentication expected failure.
The [UI guide](../UI_STYLE.md#explicit-studio-view) records native first-click
opening with preserved Unicode text, Film navigation, Escape and viewport return
on isolated offline macOS arm64 Blender 5.1.2. No service requests or paid actions
were used; the normal profile and installed package remained unchanged.
Additional offline mock-transport desktop checks cover populated-form scrolling,
quote-preserving page navigation, continued saved-job polling, shared prompt
edits with a fresh quote, and fit at 1018 × 671 with UI scale 2.0. Alternate-DPI
and IME acceptance remain open.

## Native workflow validation slice

The earlier native workflow form above #325 used ZIP SHA-256
`86894bcd18bb0df4b678b32c5785e2829f44d2f2c4a622345ee6f6663455ff2b`.
All 137 packaged Python sources match that layer. It passes 1,093 installed tests
on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, with two Windows-specific
skips per run. The unit suite passes 3,801 tests with the known SDK authentication
expected failure. Seventeen native regressions cover input/schema loading,
UI/MCP quote sharing, exact confirmation, single use, late metadata/price
rejection, scope retirement, continued jobs, saved-form/enum reconstruction,
structured always-required fields, idle cache reclamation and catalog-only delivery.
Workflow commands, Studio navigation and workflow controls are now explicitly
included in the hosted baseline's module selection; inspect the current CI run
for each platform rather than inferring those results from macOS.

After rebasing onto merged #325, ZIP SHA-256
`8f6ae6f4603d97283f8a3f5435428c2a62ff9826089064a00c88d84b34dc3c9e`
passes 1,105 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1
in isolated profiles, with two Windows-specific skips per run. All 137 packaged
Python sources match the reviewed checkout. The locked unit suite passes 3,852
tests with the same known SDK authentication expected failure. These runs retain
the merged Studio handoff checks and all seventeen workflow regressions; they
do not add physical workflow interaction or live acceptance.

At that workflow-control boundary, structured fields use JSON and file fields
accept already uploaded asset IDs. Direct reference upload/Library selection,
interactive nodes and general cancellation were incomplete. No live request or
paid generation was performed. Physical input, screenshots, layout, focus and viewport acceptance
remain pending under #66/#68 as acceptance follow-ups. Review readiness is
separate from complete product acceptance; the earlier update and release
artifact limitations still apply.

## Asset library command validation slice

The library command layer above #326 uses ZIP SHA-256
`56e0608d3d4b937c27ed05d7033132d702aac427ba511e340e48b523f279533e`.
All 137 packaged Python sources match that layer. It passes 1,100 installed tests
on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, with two Windows-specific
skips per run. The unit suite passes 3,821 tests with the known SDK authentication
expected failure; 208 focused SDK/adapter/MCP checks pass with the same expected
failure. Seven installed library tests cover scoped pagination, search bodies,
metadata projection, stale scene/project rejection and failed-read cleanup.
The authenticated MCP discovery test verifies both newly registered tools.

No live library search, file transfer, organization write or generation was
performed. Native Library presentation, integrated reference attachment and
collection/tag editing were still open at that command-layer boundary. These
command checks do not replace desktop or live release acceptance, or the final
published-artifact/update gates.

## Remaining release gates

This table dates from 2026-10-09. The
[0.10.0 evidence by lane](#0100-evidence-by-lane) and its
[pending checks](#pending-checks) supersede it where they differ. The earlier
candidate and its handoff supersede older evidence gaps only where explicitly
covered. Historical layer results below retain their own source and ZIP
identities.

| Gate | Current limit | Next evidence and owner |
| --- | --- | --- |
| Complete SDK adoption | The unscoped prototype engine and unused raw service clients are removed. The [SDK operation inventory](../SDK_ADOPTION.md#service-operation-inventory) maps maintained service paths and the existing discovery and workflow selection exceptions; offline/native checks pass. | Finish retained-capability and live provider acceptance under #64/#65; the call-site audit alone does not establish those product contracts. |
| Credentials and project scope | Merged #316 exposes an optional project ID. Scoped synthetic desktop input passed on the identified earlier ZIP; the final runtime ZIP has native regression coverage. The SDK service-retirement archive identified above also passes saved preference reload and local project isolation. | Complete fresh onboarding, permission failures, live override behavior and final-candidate update/desktop acceptance under #65/#68. |
| Compact and expanded creation | An explicit native Studio view now reuses Create, Film, Jobs, Results and Connection controls. Workflow input/approval controls now share the job session; native Library search and confirmed model/workflow-reference reuse are present, with workflow and Library interaction acceptance still open. Offline prompt handoff/editing, populated forms, scrolling, quote-preserving navigation, continued saved-job polling, small-window fit and viewport return have desktop proof; alternate-DPI and IME checks remain pending. The compact composer still needs complete retained-capability acceptance. | Complete retained Studio presentation under #66, then native select/capture/estimate/generate/inspect/apply and library reuse; focus, text input, viewport, small-window and DPI checks under #66/#68. |
| Workflows | Local MCP discovery, exact quote approval and durable execution now use the shared SDK session. Expanded Studio now has saved inputs and a separate exact-price confirmation; interactive nodes and general workflow cancellation remain absent. | Complete retained workflow presentation and authorized live output/recovery acceptance under #64/#65/#66/#68; the new commands do not close those issues. |
| Asset library | Local MCP and native Library list/search use scoped SDK reads with explicit pagination and reusable reference metadata. Native model/workflow-reference confirmation preserves scope and destination. | Complete direct workflow uploads, collection/tag organization, physical/native presentation and live acceptance under #64/#65/#66/#68. |
| Retained lanes | Existing image, material, GLB, video and audio outputs pass native application on the current candidate; the grayscale material failure is corrected by #340. These checks do not exercise the full approval journey. | Complete integrated native capture/upload/estimate/submission/application and retained render/edit/Film checks under #68 with explicit paid authorization where needed. |
| Recovery and switching | Synthetic tests cover lost acknowledgement, stale quotes, scope changes and application claims. | Candidate-level UI/MCP parity, cancellation/restart races and failed download/import journeys with recorded outcomes under #65/#68. |
| GPU, motion and audio | Human motion/audio review of the existing outputs is accepted; candidate native media insertion passes. Sustained candidate playback is unverified. | Complete native rendering/playback and sustained GPU/audio stability checks under #68; preserve the bounded human review above. |
| Paid CI | The protected `smoke` environment, maintainer reviewer, main-only policy and private secrets are configured. Zero-cap admission rejects execution; the approved hosted run produced five `READY` jobs and 16 receipt-verified files. Downloaded recovery decryption and offline resume passed without changing saved jobs. Scheduled runs use the committed image/material/audio monthly plan with a fixed 40 CU cap. | Reference-upload, uncertain-job and first monthly-run acceptance remain separate from this version-1 generation/completed-result recovery plan. No provider-side project budget is configured. |
| Required checks | `ci-ok`, `pr-title` and `commits` are required after the 2026-10-09 update. Readback confirms other integrity rules and the separate review ruleset are unchanged. CodeQL and code-quality protection remain enforced. A deliberately invalid title failed its required check while GitHub reported the administration PR blocked; the conventional title was restored. | Complete #45's documentation review/merge and verify the final PR checks; do not drop existing protections. |
| Final release artifact | The current corrected 0.9.9 ZIP passes exact-artifact native application and synthetic update/restart on all three macOS Blender versions. | Validate release-please's exact 0.10.0 ZIP, licenses, provenance/checksum and extension index; exercise public native installation/update under #36/#68 and the release procedure. |

## Native Library validation slice

The native Library layer above #327 uses the same SDK-backed asset commands with
explicit filters/page continuation and confirmed model-reference attachment.
The selected scene/form/input and connection must still match at confirmation;
existing slots are preserved and the old generation price is invalidated.
Unrelated scene edits do not discard library metadata. Workflow inputs, collection
and tag writes, thumbnails, physical interaction/screenshots and live acceptance
remain pending under #66/#68 separately from review readiness. This UI layer
does not close #64/#65/#66/#68.

Earlier candidate ZIP SHA-256
`5bd1bc29213abb62951cd69efe9e1ea9156bd6e0983e258de7cb35dcc67f7eef`
passes 1,115 installed tests on each macOS 27.0.1 arm64 Blender 5.0.1, 5.1.2 and
5.2.1, with two Windows-only skips per run. All 139 packaged Python sources match
the checkout. Each profile was isolated; normal profiles were unchanged and no
external network violations occurred. Fifteen Library regressions cover explicit
pages, filter changes, single-use owned delivery, unrelated scene edits, readonly
drawing, native confirmation dispatch, cancellation, reference type/capacity,
exact destination, selected-scene and credential/project guards. A deleted-scene
regression verifies safe dialog redraw from captured display text and rejection
of attachment to the unavailable destination. The locked unit
suite also passes with the existing SDK bearer-precedence expected failure.

After rebasing onto merged #327, ZIP SHA-256
`dc8282900cb8c1b428d258a734ebfda5e8964f3d15ecd78e73fceac1ad02d3f8`
passes 1,127 installed tests on each of those three Blender versions in isolated
profiles, with two Windows-only skips per run. All 139 packaged Python sources
match the reviewed checkout. The locked unit suite passes 3,872 tests with the
same known SDK expected failure. These runs retain all fifteen Library regressions
and the merged Studio/workflow checks; physical Library acceptance remains open.

No live or paid service calls were made. These are headless installed checks,
not physical Library interaction or release-candidate acceptance.

## Workflow Library reference validation slice

The layer above #328 adds explicit Library selection into a loaded workflow's
compatible file input. Its confirmation preserves the scene, workflow, input,
full form and selected connection; single inputs are not replaced, arrays respect
capacity, and complete requirements still apply before pricing. Persisted bindings
reject edited or cross-connection values. Clear reference(s) requires a separate
unchanged-form confirmation and keeps the documented unchecked/default semantics.

Direct workflow uploads, interactive nodes, general workflow cancellation, asset
organization and physical/live acceptance remain pending. Track desktop checks
under #66/#68 separately from review readiness. This layer does not close the
complete scope of #64/#65/#66/#68.

Earlier candidate ZIP SHA-256
`eaec050ff2c5ba67a25ac55ee9fb9eefb1e546cec7fe0cc6ea632c5a87c74d5d`
passes 1,129 installed tests on each macOS 27.0.1 arm64 Blender 5.0.1, 5.1.2 and
5.2.1, with two Windows-only skips per run. All 140 packaged Python files match
the checkout; each isolated profile was removed and normal profiles were unchanged.
Fourteen native workflow-reference tests cover incremental arrays, full validation,
shared SDK pricing and exact MCP approval, persistent scope binding/reopen, stale
forms/prices, disabled inputs, file enums, clear confirmation and removed-scene
safety. Eleven additional unit cases cover draft file edits without weakening
complete validation. The full unit suite passes 3,832 tests with the existing SDK
authentication expected failure. Synthetic transport confirms the exact reference
payload and a single approved submission without live calls or spending.

After rebasing onto merged #328, ZIP SHA-256
`5570d0629976ef38b7799dcdc3c09e5a89b188950b211c024c12add813ec4fcf`
passes 1,141 installed tests on each of those three Blender versions in isolated
profiles, with two Windows-only skips per run. All 140 packaged Python sources
match the reviewed checkout. The locked unit suite passes 3,883 tests with the
same known SDK expected failure. The fourteen workflow-reference regressions and
merged Studio/Library checks remain intact; these runs add no physical or live
acceptance.

The reviewed file-array and saved-enum fixes use ZIP SHA-256
`946fdef4d9e4ca641d1dd12e54c634d7c8f4ec8726d2c74242e0c04bb7932771`.
It passes 1,145 installed tests on each of the same three Blender versions,
with two Windows-only skips per run, unchanged normal profiles and all 140
packaged Python sources matching the checkout. The locked unit suite passes
3,889 tests with the same SDK expected failure. Eighteen workflow-reference
tests now include alternate `file`/`array: true` defaults, incremental attachment,
pricing and clearing; saved file-enum selections survive reopening, invalidate
prices when changed and require clearing before replacement. Empty saved choices
can receive a Library reference. Six additional unit cases enforce identical
array constraints for both schema spellings. These remain synthetic checks.

## Issue disposition

GitHub state reviewed on 2026-10-12 and rechecked on 2026-10-13 after #411
merged is separate from candidate acceptance:

| Scope | State and release implication |
| --- | --- |
| #64, #65, #66, #68 | Open. SDK service-path cleanup and shared commands are implemented; the [0.10.0 evidence by lane](#0100-evidence-by-lane) records retained-capability, desktop and live evidence and the [pending checks](#pending-checks). Their checklists are not yet ticked. |
| #97, #99 | Open. The model picker's trained LoRAs and compositions (#409) merged on 2026-10-12, and trained-model strengths and project defaults (#410) and MCP trained models and defaults (#411) on 2026-10-13; private trained models and a desktop recheck of the merged UI remain, and provider-specific mesh edit, rig and parts contracts remain incomplete. Local schema and application primitives do not close these scopes. |
| #98 | Open. #415's closing reference closed it on 2026-10-12, and it was reopened the same day. The native Environment lane (#416) and panorama smoke cases (#417) merged on 2026-10-12; its authorized live seam, pole and dynamic-range item and the desktop recheck of the merged lane remain. |
| #67 | Open and explicitly deferred. Browser OAuth is not required for this API-key release. |
| #31, #32, #42 | Closed for portable tooling, native baseline CI and weekly platform CI. Their infrastructure is a basis for validation, not proof of every product journey. |
| #15, #17, #43, #47, #52 | Closed for their headless CLI, capture cleanup, local MCP security, hosted link monitoring and generated MCP documentation scopes. Keep these resolved foundations closed. |
| #37 | Closed for the native update repository foundation. Exact 0.10.0 public delivery and update evidence still belong to #36/#68. |
| #36, #39, #40 | Open. The protected hosted five-lane smoke and recovery check is verified, and after #383 a free live single-part reference upload, its receipt and a bound dry-run quote passed for #40; the first approved monthly run is pending. Publication and provenance administration (#36) and action pinning (#39) retain their own gates. |
| #45 | Closed on 2026-10-09 after the required-check update. |
| #38 | Open. Changelog publication waits for the website deployment and the first published release. |
| #399, #400 | Open. The 2026-10-12 weekly macOS and Windows runs failed on a stale test expectation that #396 corrected; close after a passing rerun. |
| #189 | Open. Saved shared video and audio results have Play, Play in Blender and Waveform controls on private verified copies and receipt-keyed envelopes from an offline Blender decoder, with installed-ZIP native tests. Partial private desktop passes on macOS arm64 Blender 5.1.2 opened a saved video in the system player and in Blender's animation player at UI scale 1.0, and drew a waveform in the sidebar at UI scales 1.0 and 2.0, the last on a ZIP whose waveform status wrapped by measured width before later amendments to that wrapping; they are not candidate acceptance. Local MCP `inspect_result_previews` reads the same preview states and envelopes, with installed-ZIP native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 only. Play audio, the waveform's Cancel and Retry on the desktop, Studio at UI scale 2.0, other platforms, and native listening acceptance are not yet recorded. |
| #263 | Closed on 2026-10-04. Its public record has no documented root cause or verified fix for the historical desktop crash. Preserve the [diagnostic limits](../KNOWN_LIMITATIONS.md) and obtain current-candidate sustained desktop evidence under #68; closure alone supplies no new runtime evidence. |

On 2026-10-07, read-only administration checks found no open **CodeQL** alerts. The six open
code-scanning alerts were from **Scorecard**, which is advisory under the
[maintainer baseline](../MAINTAINERS.md). Do not treat the aggregate alert count
as six CodeQL blockers. Preserve required CodeQL/code-quality and review policies
when adding `ci-ok`; no repository settings were changed by this audit.

## Merge and release decision

Merge accepted implementation layers in dependency order and retarget descendants
after squash merges. A green implementation PR can reduce #68's remaining work
without satisfying all of it. Keep incomplete issue scope open and use `Refs`.
No issue is complete merely because historical release notes contain a closing
keyword or an older primitive was merged.

After the remaining gates pass, replace the candidate identity above with the
actual release candidate, retain failing/unsupported environments explicitly and
follow [the release procedure](../RELEASING.md). Public delivery and changelog
checks that require the published build must be recorded with that build's
provenance; do not report them in advance.
