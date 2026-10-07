# Consolidated extension release acceptance

Release [#70](https://github.com/scenario-labs/blender-plugin/pull/70) remains on
hold under [#68](https://github.com/scenario-labs/blender-plugin/issues/68).
This record identifies the tested integration candidate and the evidence still
needed before releasing 0.10.0. It does not replace the
[release plan](release-plan.md), narrow retained-lane acceptance or authorize
publication. OAuth remains deferred under #67.

## Candidate identity

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

## Verified evidence

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

## Remaining release gates

| Gate | Current limit | Next evidence and owner |
| --- | --- | --- |
| Complete SDK adoption | The unscoped prototype engine and unused raw service clients are removed. The [SDK operation inventory](../SDK_ADOPTION.md#service-operation-inventory) maps maintained service paths and the existing discovery exception; offline/native checks pass. | Finish retained-capability and live provider acceptance under #64/#65; the call-site audit alone does not establish those product contracts. |
| Credentials and project scope | Merged #316 exposes an optional project ID. Scoped synthetic desktop input passed on the identified earlier ZIP; the final runtime ZIP has native regression coverage. The SDK service-retirement archive identified above also passes saved preference reload and local project isolation. | Complete fresh onboarding, permission failures, live override behavior and final-candidate update/desktop acceptance under #65/#68. |
| Compact and expanded creation | The expanded composer remains a generation card; the optional expanded Studio and its workflow/asset-library forms are not implemented. Earlier screenshots also do not establish the complete candidate journey. | Complete retained Studio presentation under #66, then native select/capture/estimate/generate/inspect/apply and library reuse; focus, text input, viewport, small-window and DPI checks under #66/#68. |
| Workflows | Local MCP discovery, exact quote approval and durable execution now use the shared SDK session. Expanded Studio forms, interactive nodes and general workflow cancellation remain absent. | Complete retained workflow presentation and authorized live output/recovery acceptance under #64/#65/#66/#68; the new commands do not close those issues. |
| Retained lanes | Offline receipts and MIME checks do not establish usable live results. | Authorized scoped checks for Image, Video, 3D, Materials, audio, render/edit and Film paths; inspect actual outputs and record limitations under #68. |
| Recovery and switching | Synthetic tests cover lost acknowledgement, stale quotes, scope changes and application claims. | Candidate-level UI/MCP parity, cancellation/restart races and failed download/import journeys with recorded outcomes under #65/#68. |
| GPU, motion and audio | Headless counts and media metadata do not establish sustained playback or human review. | Native rendering/playback, sustained GPU/audio checks and human motion/audio review under #68. |
| Paid CI | The suite runner and protected workflow now quote all cases and enforce one aggregate cap. Explicit version-2 reference plans now stage/upload through shared durable commands before quoting. A read-only 2026-10-08 check finds no `smoke` environment; live reference-upload acceptance remains pending. | Configure #40's explicit project/budget policy, environment reviewers, private plan, recovery encryption secret and dedicated credentials; complete authorized hosted upload/generation acceptance. |
| Required checks | Read-only main-branch rules checked on 2026-10-08 report `pr-title` and `commits` as required, plus CodeQL scanning. `ci-ok` is absent. | Complete #45's administration and negative merge-gate checks while preserving existing protections. |
| Final release artifact | Current candidate retains development version 0.9.9. Local update checks use a synthetic predecessor. | Validate release-please's exact 0.10.0 ZIP, licenses, provenance/checksum and extension index; exercise public native installation/update under #36/#68 and the release procedure. |

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
