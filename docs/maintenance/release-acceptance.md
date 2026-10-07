# Consolidated extension release acceptance

Release [#70](https://github.com/scenario-labs/blender-plugin/pull/70) remains on
hold under [#68](https://github.com/scenario-labs/blender-plugin/issues/68).
This record identifies the tested integration candidate and the evidence still
needed before releasing 0.10.0. It does not replace the
[release plan](release-plan.md), narrow retained-lane acceptance or authorize
publication. OAuth remains deferred under #67.

## Candidate identity

Reviewed on 2026-10-07:

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

A non-submitting live Image model metadata/estimate request succeeded. No paid
generation, live upload/result round trip or project-override permission journey
is included in this record. Quote values and private service evidence are not
published here.

## Remaining release gates

| Gate | Current limit | Next evidence and owner |
| --- | --- | --- |
| Complete SDK adoption | Shared model jobs and scoped recovery have extensive regression coverage; that alone does not audit every ancillary call site or retained capability. | Reconcile the runtime map and remaining call sites against #64/#65; identify each SDK method or documented exception. |
| Credentials and project scope | #316 exposes an optional project ID and tests scope switching, stale approvals and in-flight receipt ownership. | Complete fresh native setup/input, permission failures, live override behavior and saved preference reload under #65/#68. |
| Compact and expanded creation | Earlier screenshots and isolated controls do not establish the complete journey on this candidate. | Native select/capture/estimate/generate/inspect/apply and library reuse; focus, text input, viewport, small-window and DPI checks under #66/#68. |
| Retained lanes | Offline receipts and MIME checks do not establish usable live results. | Authorized scoped checks for Image, Video, 3D, Materials, audio, render/edit and Film paths; inspect actual outputs and record limitations under #68. |
| Recovery and switching | Synthetic tests cover lost acknowledgement, stale quotes, scope changes and application claims. | Candidate-level UI/MCP parity, cancellation/restart races and failed download/import journeys with recorded outcomes under #65/#68. |
| GPU, motion and audio | Headless counts and media metadata do not establish sustained playback or human review. | Native rendering/playback, sustained GPU/audio checks and human motion/audio review under #68. |
| Paid CI | #315 unifies quote/submit/resume and per-run exact approval. There is no protected multi-suite workflow or aggregate budget gate; the repository has no `smoke` environment. | Complete #40's protected workflow, explicit project/budget policy, environment reviewers and dedicated credentials; then perform authorized hosted acceptance. |
| Required checks | Read-only main-branch rules report `pr-title` and `commits` as required, plus CodeQL scanning. `ci-ok` is absent. | Complete #45's administration and negative merge-gate checks while preserving existing protections. |
| Final release artifact | Current candidate retains development version 0.9.9. Local update checks use a synthetic predecessor. | Validate release-please's exact 0.10.0 ZIP, licenses, provenance/checksum and extension index; exercise public native installation/update under #36/#68 and the release procedure. |

The #316 desktop attempt used the preceding candidate
`4d85cd66cde982d71ff012c942db95c25615628cde072fed1a0e8e61b927cc89`.
It opened an isolated fixture, but computer control failed to target the window
for native input or screenshots (`cgWindowNotFound`). A separate test-only app
identifier had the same limitation. Successful fixture exits preserved the normal
profile and made no external requests. This is a recorded environment limitation,
not a pass; #316 remains draft until native proof is supplied.

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
