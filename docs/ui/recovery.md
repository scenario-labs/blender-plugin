# Blockout plans and cloud recovery

Interaction rules and desktop evidence for Blockout plans and recovering cloud
jobs. The shared rules are in the [UI style guide](../UI_STYLE.md).

## Blockout plan approval interaction

Blockout prices a settled description automatically and shows **Generate
blockout (cost)**; **New plan** or **Try again** requests one by hand for unchanged
or refused inputs. Refine has its own quote. A completed plan exposes **Build
blockout**; generation itself leaves geometry unchanged. Clear opens a confirmation
dialog. Drawing is read-only.

The exact ZIP with SHA-256
`44edc43008d64f1e2836c95c0cb526f5c727a4278f6468676d4d7ef71b8fc47e`
passed 732 installed native tests each on macOS arm64 Blender 5.0.1, 5.1.2 and
5.2.1. An isolated 5.1.2 desktop check edited the prompt with native input,
requested a quote with zero submissions, approved once, and received a plan
without changing geometry. Build created the grouped tower while the existing
cube remained selected. Native Edit > Undo removed the tower and restored the
earlier empty plan; Redo restored both. Cancelling Clear preserved the result.
Viewport zoom and front-view input remained available. The single mock submission
and eight total mock requests did not increase during local operations.
The test exited cleanly and verified the normal profile fingerprint unchanged.

The transport and tower were synthetic; the frozen Connecting label is fixture
state, not service performance evidence. The initial fixture failed while waiting
for the sidebar region and exited without profile changes; the completed repeat
waited for that region. Native runs retain a small Blender shutdown allocation
diagnostic. Live provider compatibility, other OS desktop behavior and explicit
recovered-plan import into a new scene are not established by these checks.

[Before quote approval](../images/blockout-plan-approval.png).

![Blockout geometry after build, native undo and redo](../images/blockout-plan-built.png)

The refinement-instruction follow-up uses ZIP SHA-256
`5c66b30ebe403ab46658fa556fa906fd49dcd2a48816d7867f18c5ab83a27c42`,
with 732 installed tests passing on each of the same three Blender versions.
It replaces mixed design/refinement wording with the explicit complete-plan
update instruction. The desktop interaction and screenshots above use the
preceding ZIP; no new UI behavior or live provider acceptance is claimed here.

## Saved Blockout plan recovery

Saved jobs expose **Read saved Blockout plan**, followed by **Use saved Blockout
plan** after complete text validation. The confirmation names the scene and
element/group counts, warns before replacing an existing plan and explains that
geometry remains unchanged until a separate Build blockout action. Cancellation
discards the review. Drawing does not read the service or mutate the plan.

The exact package with SHA-256
`9b9bb818f0ec81e0af4ed95ba6d70390d17e12af72c24b5040d6814316b31ed2`
passes 740 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.
These cover native operator execution, MCP parity, restart with and without a
saved manifest, discarded/single-use reviews, changed fields and scene
replacement, retired contexts, offline reads and malformed text. Saved-job
drawing skips invalid scene references, and status reports a deleted scene
without rebinding a same-name replacement.

![Saved Blockout job offers a separate read action before destination approval](../images/blockout-recovery-controls.png)

Desktop interaction with the same ZIP passes on macOS arm64 Blender 5.1.2 in an
isolated profile, using a synthetic saved job and blocked external networking:

- **Read saved Blockout plan**, then **Use saved Blockout plan**, opens the
  destination/count/replacement dialog. Escape cancels and discards the review
  while preserving the previous stored plan and all geometry.
- After a fresh read, Return confirms the dialog and replaces only the stored
  plan. Blender's **Edit > Undo** restores the previous plan; **Edit > Redo**
  reapplies the recovered plan. Geometry stays unchanged throughout.
- A viewport click selects the existing cube, and Home frames the scene,
  confirming viewport focus and keyboard navigation after the dialog.
- A separate **Build plan** click creates the recovered tower and preserves the
  existing cube, light and camera. Approval, Undo/Redo, viewport interaction and
  building issue no further service requests or submissions.

![Saved Blockout plan confirmation names the destination and preserves geometry until Build](../images/blockout-recovery-approval.png)

![Separate Build plan action creates the recovered tower beside the preserved cube](../images/blockout-recovery-built.png)

The test app uses the vendor Blender binary and the unchanged extension ZIP;
the harness removes its disposable profile after the interaction. The normal
profile remained unchanged. Transport and plan contents are synthetic, with no
live generation. This proves the scoped recovery interaction at the tested
window size, not other OS/DPI combinations, live provider behavior or integrated
release acceptance.

The recovery review fixes were retested with ZIP SHA-256
`b0bc4c291aa5d910beb53d34974526c74e5971d3462b326006cb521c697faeec`:
746 installed tests pass on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.
These add deleted-destination review cleanup, pending-read drainage, finished
action reclamation without retiring uncertain jobs, and guided invalid-plan
refinement errors before any quote request. Desktop checks on Blender 5.1.2
repeat Escape cancellation, Return confirmation, stored-plan Undo/Redo and
separate Build; viewport front-view and zoom input work afterward. The synthetic
fixture establishes an Undo checkpoint after preparing its starting scene.
Local approval, Undo/Redo and Build add no service request or submission; both
disposable runs exit cleanly with the normal profile unchanged. The screenshots
above retain their original artifact provenance. These checks do not establish
live provider or integrated release acceptance.

## Cloud history recovery controls

A cloud row matched to the current scoped job store offers **Inspect saved jobs**
instead of **Download and open**. Its saved-job controls retain the explicit
download and destination-approval steps. Drawing uses the saved-ID snapshot from
explicit history reads plus live shared-job views, without database I/O, session
activation, service requests or scene/job changes. Import commands independently
recheck current storage. A changed credential selection hides the old row actions
until refresh; a failed saved read disables those actions until a successful read.

Each row's price adds the job's documented add-on charges to its main charge.
A workflow run has its own row with the node-tree icon and the sum of its step
charges; when a step cannot be read, it shows **Cost unavailable** rather than
0 CU. Its steps keep their rows with a linked note that they are included in
the run's total once it is known, which stays true while the run is running or
its cost is unavailable. A row whose own charge is malformed also shows
**Cost unavailable**, while the other rows still load. Workflow rows offer no
**Save for recovery**; their model steps do. Step reads happen on the history
worker, never while drawing.

The exact ZIP with SHA-256
`30b0e2c03268e81a64ad83d0cc2924be9d0afaac8d7aebf9a80b3aafc9349b2c`
passes 749 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.
Regressions cover native operator execution, read-only draw routing, stale-page
acknowledgement, old-cache collisions, missing storage, restart and credential
changes, including rejecting MCP import with incomplete credentials. These are
synthetic installed tests.

Desktop input with the same ZIP passes on macOS arm64 Blender 5.1.2 in an isolated
profile. The fixture preloads a synthetic cloud page, a matching scoped saved
job and a colliding old cache entry. Clicking **Project history (cloud)** shows
**Inspect saved jobs** on the matching row. Clicking it opens the shared recovery
controls with a separate **Resume download** action. It does not import the old
file or change the saved record, scene objects or images. The request count stays
unchanged, and neither legacy import dispatch nor job tracking runs.

![Matching cloud history row offers Inspect saved jobs before any download or import](../images/history-saved-job-row.png)

A viewport click selects the light, and Home frames the scene, confirming focus
and keyboard navigation after inspection. The harness closes the test and removes
its disposable profile; the normal profile remains unchanged. External networking
is blocked. This proves the scoped row-to-recovery interaction, not a live cloud
refresh, download/import completion, arbitrary cloud-job adoption, other OS/DPI
combinations or integrated release acceptance.

![Shared saved-job recovery offers Resume download while the existing scene remains intact](../images/history-saved-job-recovery.png)

The redraw fix uses ZIP SHA-256
`27ebeece6da712d7b6fd50a8047736df8351e501679b1a4ad1503b62f82e7ac5`.
All 751 installed tests pass on each of the same three Blender versions.
Regressions reject database reads during 30 consecutive panel draws, retain
saved-job routing for late shared-view acknowledgements, and verify storage
failure/retry and credential-change invalidation. The existing screenshots and
desktop interaction evidence above belong to the preceding ZIP; desktop input
on the changed artifact remains unverified.

## Completed cloud job recovery controls

A successful cloud row without a scoped record offers **Save for recovery**.
The metadata read is available in Edit, Sculpt and Pose modes as well as Object
mode, subject to the same online-access and credential checks. Switching scenes
while it runs does not discard the saved record or authorize scene application.
Admission errors show their actionable reason, such as a different model read
already pending for that job; unexpected failures keep a generic sanitized message.
While its shared worker reads the job, the disabled label is **Reading cloud
job...**. Success exposes **Inspect saved jobs** and a paused recovery record;
download and destination approval remain separate. A sanitized read error allows
an explicit retry. Legacy cache rows and files cannot substitute their old
actions or hide this control. Drawing only inspects the current store/facade.
Saved recovery rows keep their place when prototype jobs report progress or the
application pump runs again. A shared row takes precedence over a legacy row
with the same local ID. The prototype's 50-row limit does not trim saved recovery
rows. These are display rules; they do not delete stored jobs or resume work.

The exact ZIP with SHA-256
`e572909c23aae8ddd027aa48e489f338eb34dd35b2eacdaf35cbb9a7c57f11ec`
passes 760 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.
Native desktop interaction with that same ZIP passes on macOS arm64 Blender
5.1.2 in a disposable profile. The fixture preloads one synthetic cloud row and
uses the real installed SDK adapter with a GET-only mock transport; external
Python network connections are blocked.

![Cloud history offers Save for recovery while the scene remains unchanged](../images/cloud-history-recovery-controls.png)

Clicking **Save for recovery** starts one job read and disables the pending
control. Pressing N closes the sidebar while that read is held by the fixture.
Releasing the synthetic response delivers one paused cloud record with the
sidebar still closed. Reopening it shows **Resume download**. Repeated
**Inspect saved jobs** does not alter the record or issue another request.
The scene's objects and images remain unchanged, with zero downloads or paid
submissions. A subsequent viewport click selects the light, and Home frames
the scene, confirming mouse focus and keyboard navigation after recovery.

![Recovered cloud job waits for Resume download without importing any result into the scene](../images/cloud-history-recovery-saved.png)

A separate run exercised a sanitized read rejection after selection changed
while the read was pending; explicit retry saved one paused record without a
submission or download. Both completed runs exit through harness cleanup, remove
their disposable profiles and leave the normal profile unchanged. The isolated
application has a test-only identifier to distinguish its window; the extension
ZIP is unchanged. These checks establish native recovery controls with synthetic
responses, not live cloud history, provider latency, completed result application,
other OS/DPI combinations or integrated release acceptance.

Scene-independent metadata delivery has separate native input proof on macOS
arm64 Blender 5.1.2, using exact ZIP SHA-256
`38f0a51edea77643f4988c737090e759b578c4b1844cdfd25f4ec43c3f3183d6`.
That ZIP passes 822 installed tests on each Blender 5.0.1, 5.1.2 and 5.2.1.
With external network connections blocked and a GET-only SDK fixture, clicking
**Save for recovery** in Edit Mode starts one metadata read. While it is held,
Tab exits Edit Mode, the scene selector switches to another scene, and N hides
the sidebar. The response saves one paused record while that sidebar is closed.
Reopening it shows **Resume download** in the second scene. Repeated inspection
leaves the record and request count unchanged; neither scene receives a result.
Returning to the original scene, selecting the light and pressing Home confirms
viewport mouse focus and keyboard framing. There are zero downloads or paid
submissions, cleanup removes the disposable profile, and the normal profile is
unchanged. Sculpt/Pose admission and actionable admission errors have installed
regression coverage; this desktop run exercised Edit Mode and scene switching.
The live-provider, other-OS and release limitations above still apply.

![Save for recovery is enabled in Edit Mode](../images/cloud-recovery-edit-mode.png)

![The paused cloud record survives switching to another scene](../images/cloud-recovery-scene-switch.png)

## Unconfirmed submission recovery controls

A saved job whose submission Scenario never confirmed shows **Submission not
confirmed** and, under it, the cloud lookup's note: **Looking in cloud
history...**, **N possible cloud jobs found**, **No matching cloud job found**
or the reason a lookup or link failed. Blender looks once per session for each
such job it shows while Online Access is allowed; **Find in cloud history** looks
again. Both only read Scenario's job list.

While candidates are listed, **Choose cloud job...** opens a dialog that says
Scenario cannot tell which job the request created, that linking cannot be
undone and that results still need review. Each candidate shows when it was
created relative to sending (or its UTC time when the send time is unknown), its
status and cost on one line and its prompt on the next. No job is selected at
first; **Link this job** without a choice links nothing. A link Scenario's fresh
retrieval refuses keeps the job unconfirmed and shows why. A saved link turns
the row into an ordinary running job, polled and downloaded as usual; its
results wait for review, even on the Image lane that sent the request. **Mark
reviewed** stays available. The compact job strip still offers only **Inspect**
for these jobs.

A finished prompt helper job offers **Read prompt text**, then a preview and
**Copy prompt text** for each text. In the session that sent it, a prompt action
stopped by an unconfirmed submission fills its unchanged field once the linked
job finishes.

Installed tests cover the candidate dialog's operator and the link flow for a
model, a workflow and a prompt helper job with a synthetic SDK transport. The
desktop check of the dialog, its focus and viewport input afterward is pending.
