# Consolidated extension release acceptance

Release [#70](https://github.com/scenario-labs/blender-plugin/pull/70) remains on
hold under [#68](https://github.com/scenario-labs/blender-plugin/issues/68).
This record identifies the tested integration candidate and the evidence still
needed before releasing 0.10.0. It does not replace the
[release plan](release-plan.md), narrow retained-lane acceptance or authorize
publication. OAuth remains deferred under #67.

## Current candidate and decision

Reviewed on 2026-10-09 after the implementation stack merged. The supported
release remains held by #68. The current development candidate includes the
[grayscale material fix, #340](https://github.com/scenario-labs/blender-plugin/pull/340),
which must merge before its dependent acceptance record.

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
macOS ZIP. Check the current fix and acceptance PR heads before merging.

### Remaining acceptance handoff

The merged-main exact-ZIP desktop session launched in the isolated review app
and exited cleanly with its normal profile unchanged. The computer-control
service failed at native-pipe startup, including after a reset, before any
interaction or screenshot could be verified. This is a tool attachment failure,
not evidence that Blender crashed or that UI checks passed. The corrected ZIP
has no new physical desktop evidence. Earlier desktop evidence below retains
its own artifact identity.

Complete these checks on the corrected candidate before releasing:

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
5. Required CI enforcement (#45), protected hosted smoke acceptance (#40), and
   explicit experimental/unavailable capability limits. A later read-back on
   2026-10-09 confirms required `ci-ok`, `pr-title` and `commits`, plus the protected
   main-only `smoke` environment. Hosted smoke execution and its explicit budget
   still need acceptance. See the [current administration record](../MAINTAINERS.md)
   and #45 for live merge-gate evidence. No settings were changed by this read-back.
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

The current candidate and concrete handoff above supersede earlier evidence gaps
only where explicitly covered. Historical layer results below retain their own
source and ZIP identities.

| Gate | Current limit | Next evidence and owner |
| --- | --- | --- |
| Complete SDK adoption | The unscoped prototype engine and unused raw service clients are removed. The [SDK operation inventory](../SDK_ADOPTION.md#service-operation-inventory) maps maintained service paths and the existing discovery exception; offline/native checks pass. | Finish retained-capability and live provider acceptance under #64/#65; the call-site audit alone does not establish those product contracts. |
| Credentials and project scope | Merged #316 exposes an optional project ID. Scoped synthetic desktop input passed on the identified earlier ZIP; the final runtime ZIP has native regression coverage. The SDK service-retirement archive identified above also passes saved preference reload and local project isolation. | Complete fresh onboarding, permission failures, live override behavior and final-candidate update/desktop acceptance under #65/#68. |
| Compact and expanded creation | An explicit native Studio view now reuses Create, Film, Jobs, Results and Connection controls. Workflow input/approval controls now share the job session; native Library search and confirmed model/workflow-reference reuse are present, with workflow and Library interaction acceptance still open. Offline prompt handoff/editing, populated forms, scrolling, quote-preserving navigation, continued saved-job polling, small-window fit and viewport return have desktop proof; alternate-DPI and IME checks remain pending. The compact composer still needs complete retained-capability acceptance. | Complete retained Studio presentation under #66, then native select/capture/estimate/generate/inspect/apply and library reuse; focus, text input, viewport, small-window and DPI checks under #66/#68. |
| Workflows | Local MCP discovery, exact quote approval and durable execution now use the shared SDK session. Expanded Studio now has saved inputs and a separate exact-price confirmation; interactive nodes and general workflow cancellation remain absent. | Complete retained workflow presentation and authorized live output/recovery acceptance under #64/#65/#66/#68; the new commands do not close those issues. |
| Asset library | Local MCP and native Library list/search use scoped SDK reads with explicit pagination and reusable reference metadata. Native model/workflow-reference confirmation preserves scope and destination. | Complete direct workflow uploads, collection/tag organization, physical/native presentation and live acceptance under #64/#65/#66/#68. |
| Retained lanes | Existing image, material, GLB, video and audio outputs pass native application on the current candidate; the grayscale material failure is corrected by #340. These checks do not exercise the full approval journey. | Complete integrated native capture/upload/estimate/submission/application and retained render/edit/Film checks under #68 with explicit paid authorization where needed. |
| Recovery and switching | Synthetic tests cover lost acknowledgement, stale quotes, scope changes and application claims. | Candidate-level UI/MCP parity, cancellation/restart races and failed download/import journeys with recorded outcomes under #65/#68. |
| GPU, motion and audio | Human motion/audio review of the existing outputs is accepted; candidate native media insertion passes. Sustained candidate playback is unverified. | Complete native rendering/playback and sustained GPU/audio stability checks under #68; preserve the bounded human review above. |
| Paid CI | The suite runner and protected workflow now quote all cases and enforce one aggregate cap. Explicit version-2 reference plans now stage/upload through shared durable commands before quoting. The 2026-10-09 read-back confirms the main-only `smoke` environment, one required reviewer and required secret names; the scheduled budget variable is unset and no hosted run is recorded. | Validate #40's private plan, credentials/scope and recovery secret without publishing their values; agree an explicit budget and complete authorized hosted upload/generation acceptance. |
| Required checks | Read-only main-branch rules checked on 2026-10-09 require `ci-ok`, `pr-title` and `commits` from GitHub Actions, plus CodeQL and code-quality enforcement. Integrity has no bypass. | Record #45's live negative/positive merge-gate check and merge the matching administration documentation; preserve existing protections. |
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

GitHub state reviewed on 2026-10-07 is separate from candidate acceptance:

| Scope | State and release implication |
| --- | --- |
| #64, #65, #66, #68 | Open. SDK service-path cleanup and shared commands are implemented in the candidate; complete retained-capability, native journey and live provider acceptance still need evidence. |
| #97, #98, #99 | Open. Trained/custom-model routing, panoramic generation, and provider-specific mesh edit/rig/parts contracts remain incomplete. Local schema/application primitives do not close these scopes. |
| #67 | Open and explicitly deferred. Browser OAuth is not required for this API-key release. |
| #31, #32, #42 | Closed for portable tooling, native baseline CI and weekly platform CI. Their infrastructure is a basis for validation, not proof of every product journey. |
| #15, #17, #43, #47, #52 | Closed for their headless CLI, capture cleanup, local MCP security, hosted link monitoring and generated MCP documentation scopes. Keep these resolved foundations closed. |
| #37 | Closed for the native update repository foundation. Exact 0.10.0 public delivery and update evidence still belong to #36/#68. |
| #36, #39, #40, #45 | Open. Publication/provenance administration, action pinning, protected paid smoke acceptance and required-check enforcement retain their own gates. |
| #189 | Open. A local PCM WAV waveform preview exists; broader audio preview and native listening acceptance are not complete. |
| #263 | Closed on 2026-10-04. Its public record has no documented root cause or verified fix for the historical desktop crash. Preserve the [diagnostic limits](../KNOWN_LIMITATIONS.md) and obtain current-candidate sustained desktop evidence under #68; closure alone supplies no new runtime evidence. |

Read-only administration checks found no open **CodeQL** alerts. The six open
code-scanning alerts were from **Scorecard**, which is advisory under the
[maintainer baseline](../MAINTAINERS.md). Do not treat the aggregate alert count
as six CodeQL blockers. Preserve required CodeQL/code-quality and review policies
when maintaining required checks; no repository settings were changed by this audit.

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
