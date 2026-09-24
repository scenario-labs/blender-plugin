# API-key release plan

The current release uses explicitly configured API key/secret credentials with
optional project selection. Browser OAuth is deferred under
[#67](https://github.com/scenario-labs/blender-plugin/issues/67); it must not block
independent implementation or be claimed complete. This changes the release
onboarding gate, not the mandatory SDK-first, scope, spend or scene-safety rules.

## Candidate acceptance

[#68](https://github.com/scenario-labs/blender-plugin/issues/68) owns the release
candidate evidence. The candidate must demonstrate:

- Fresh API-key setup, an explicit credential source, optional project scope,
  understandable permission failures and invalidation after credentials change.
- One SDK-backed command/runtime path shared by the UI and authenticated local
  MCP, with exact quotes and no duplicate paid dispatch after uncertainty.
- Durable jobs, cancellation, result download/application recovery and explicit
  handling of stale scenes or targets. View closure must not own job lifetime.
- A usable compact default and native sidebar, with expanded Studio opened only
  explicitly; retained capabilities remain available through the shared runtime.
- Safe mesh/World and other result application with meaningful native tests.
- A tested installed ZIP, required dependency licenses, truthful user guidance,
  declared native support and Blender-native update discovery/install.

Film and unaccepted provider/capability paths retain explicit experimental or
unavailable status. No broad capability acceptance follows from importing a
schema, helper or upstream source file.

## Delivery sequence

PR boundaries may change as integration reveals dependencies. Existing issues
remain the source of acceptance; this sequence does not duplicate their scope.

| Sequence | Work | Owner |
| --- | --- | --- |
| 1 | Reconcile the API-key release gate and merged foundations | #64, #65, #67, #68 |
| 2 | Local MCP request/authentication safeguards, Python gate, private capture cleanup and working headless CLI | #15, #17, #43 |
| 3 | Explicit credentials/project context, manifest permissions and safe credential-change behavior | #16, #65, #67 (OAuth portion deferred) |
| 4 | Durable result inventory, download verification and application recovery | #65 |
| 5 | One SDK-backed command/runtime service with catalog, quotes and submission | #64, #65 |
| 6 | Reference capture/upload orchestration, cancellation and restart recovery | #65 |
| 7 | Route UI and local MCP through shared commands and retire active duplicate paths | #53, #64, #65 |
| 8 | Compact/native and explicit expanded view integration, with native interaction proof | #66 |
| 9 | Model discovery/routing and complete mesh/World result journeys | #97, #98, #99 |
| 10 | Single public guide, generated MCP reference, privacy/support/security and contributor guidance | #2, #12, #13, #22, #48, #51, #52 |
| 11 | Hosted validated extension repository and native update actions | #37, #56 |
| 12 | Exact candidate ZIP, scoped live smoke, native desktop/platform acceptance and release verification | #32, #36, #40, #42, #45, #68 |

The existing cancellation, transfer, origin, upload, schema, mesh and World
primitives are merged. See the [runtime map](../architecture/runtime.md) for what
is connected today; the plan is not a claim that the active prototype has already
been replaced. Mechanical normalization and source provenance must remain
reviewable when adopting retained source under #28/#64.

## Evidence and publication

Each PR records its final scope, relevant regression/native evidence and any
remaining acceptance. Close an issue only after its complete current criteria
are satisfied. Keep one source of release/package versioning and do not manually
bump versions in implementation PRs.

Offline fixtures and non-spending checks come first. A paid smoke run needs a
specific authorized project and budget before it starts. Native interaction and
human motion/audio acceptance cannot be inferred from synthetic handlers or a
headless test count. Release publication is a separate final step after candidate
acceptance; the release PR remains on hold until then.
