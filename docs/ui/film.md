# Film controls

Interaction rules and desktop evidence for Film tasks, shots, capture, timeline, composition, review, export and case studies. The shared rules are in the [UI style guide](../UI_STYLE.md).

## Film task controls

Film tasks occupy an optional, initially closed **Film** sidebar panel. Loading
a recipe validates it before changing persistent scene properties and preserves
the production identity. Task rows are saved properties, not transient enums or
mutations during drawing. **New production** requires confirmation.

**Use saved upload** opens a cached list of imported uploads and confirms the
unchanged task, recipe, production, scene and connection before association.
**Estimate task** makes a free quote request; the separate **Generate** confirmation
shows its exact decimal CU price and states that results remain saved for explicit
application. The panel draws cached handles only; it does not open storage or
contact Scenario.

Current submitted and associated task rows show **Submission saved** or
**Upload associated**, without offering another estimate or association action.
The maintenance pump invalidates ready prices when their captured scene revision
changes, and approval rechecks before persistence. Drawing remains read-only.

Offline desktop acceptance on macOS arm64 Blender 5.1.2 used exact ZIP SHA-256
`b1ad71d94a1355bc7d8d825b4d1232b7a14cf91c53d8c11aa37737e4a0907590`,
which separately passed 799 installed tests on each supported Blender series.
Native mouse input loaded the JSON through Blender's file picker and selected
both task rows. Escape cancelled upload association without saving it; Return
confirmed the separate association. The Generate dialog displayed the full
synthetic price `0.1234567890123456789 CU`. Escape preserved the ready estimate
without submitting; the automated-GUI-probe guard also rejected approval without
creating a job. Discarding released that estimate.

With the fixture's SDK transport and result bytes mocked and external sockets
blocked, a fresh quote and explicit confirmation produced exactly one saved job
and one downloaded result. The result stayed ready for explicit application;
objects and image datablocks were unchanged. Re-estimating the reserved task was
rejected without another submission. Cancelling New production preserved its
identity; confirming changed it while retaining the recipe and previous job.
Viewport Light selection and Home framing worked after the dialogs. The isolated
run exited cleanly, removed its test profile and left the normal profile unchanged.
The test-only Blender app copy had a distinct bundle identifier and local signature;
the vendor executable code and extension ZIP were unchanged.

![Film approval displays the exact synthetic price before confirmation](../images/film-task-approval.png)

![One Film submission is saved while the scene remains unchanged](../images/film-task-saved.png)

These are offline interaction checks, not live pricing or provider acceptance.
The screenshots and desktop evidence above predate the current stale-price and
saved-row review fixes. Those changes have separate installed native regression
coverage; fresh physical input and screenshot proof remain pending.
They do not establish other OS desktop behavior, Film scene construction/capture,
finishing/export, resolution of #263 or integrated release acceptance.

### Film shot controls

The **Shots** child panel uses saved shot rows and a stable selected index.
**Prepare shot** presents saved GLB choices per hero before local verification;
**Build shot** requires a second confirmation naming the shot, recipe scene and
hero count. The build preserves the working scene. **Discard review** confirms
discarding unapproved work. **Save build receipt** never repeats a scene build.
**Acknowledge inspection** requires a checkbox and cannot clear saved uncertainty.
**Shot error details** wraps the complete cached error and offers copying.
Drawing uses cached status and never starts a session or polls storage/workers.

Installed synthetic tests cover UI/MCP handle sharing, source/build cancellation,
changed destinations, receipt-only recovery, strict inspection acknowledgement,
saved shot selection and read-only drawing. Exact ZIP SHA-256
`f590b4ef5a601e984d1d0b950f0b5119b764347bd3e3aa4e2b8cc5b26ab14c09`
passes 855 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.

Desktop interaction with that same ZIP passes on macOS arm64 Blender 5.1.2 in
an isolated profile. The fixture supplies two saved synthetic hero GLBs and
blocks external Python sockets. Native mouse input expands Film and opens the
source review; Escape cancels it without creating a review or claiming jobs.
Return confirms local verification. Cancelling the separate Build shot dialog
preserves the ready review, jobs and scenes. Confirmed Discard review retires
only that unapproved review.

![Film build approval names the shot and two saved hero models](../images/film-shot-approval.png)

Fresh verification and explicit build confirmation create exactly one shot scene
and save both application receipts while preserving the selected working scene
and its objects. Edit > Undo removes that shot; Edit > Redo restores it. Neither
action rewinds the saved job receipts or permits reuse of the consumed review.
After history invalidates the original scene handles, the panel offers fresh
preparation. A viewport click selects the light and Home frames the scene,
confirming focus and keyboard navigation. The native scene selector opens the
built shot and returns to the intact working scene.

![Film reports the completed shot while keeping the working scene selected](../images/film-shot-built.png)

The run records zero service requests and downloads, exits cleanly, removes its
disposable profile and leaves the normal profile unchanged. This establishes the
synthetic shot-control interaction, not live provider compatibility, motion/audio
review, other OS/DPI combinations, timeline/capture/finishing or release acceptance.

### Film capture controls

The **Capture** child panel uses the shot selected in **Shots**. **Render capture**
confirms a matching local scene, still/video, color mode, dimensions and exact
editorial timing. It names optional video tools and distinguishes generated
source duration/trim from captured frames. Cancelling is inert. Prepared MCP
reviews expose **Render prepared capture** with the same exact settings.

Completed output offers **Open capture** and a separate **Upload capture**
confirmation showing size, timing, dimensions and full content hash.
**Cancel capture** retains frames after stopping work. **Discard capture**
confirms deleting only private capture files after work ends; saved uploads
remain. Failed work exposes its retained directory and wrapped cached error.
Drawing reads cached review status, never starts work or mutates properties.
The shared maintenance pump owns progress even with the panel closed.

Installed synthetic tests cover commands, cancellation, read-only drawing and
byte-checked upload handoff. Exact ZIP SHA-256
`50ab56cd3e12fa2991fb0cd3189cca3e9a7d3d700f4c9d13cfbee75bf64a4a85`
passes 892 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.

Desktop interaction with that same ZIP passes on macOS arm64 Blender 5.1.2 in
an isolated profile. The synthetic fixture blocks external Python sockets and
uses the real offline child renderer. Native keyboard input edits the dimensions;
Escape cancels capture approval without rendering, upload or scene changes.
A fresh dialog accepts a 128 by 128 still with material colors and one frame.

![Film capture approval shows the selected shot, dimensions and timing](../images/film-capture-approval.png)

The rendered PNG's bytes match its recorded hash. All original scenes, objects,
frames and render settings remain unchanged, and no generation job is created.
Collapsing and reopening Film preserves the completed capture. The separate
upload dialog shows its size, dimensions, timing and full content hash. Escape
preserves the local capture without creating an upload or calling the transport.

![Film upload approval identifies the exact captured bytes](../images/film-capture-upload-approval.png)

Confirmed upload uses a mocked SDK transport and one synthetic byte transfer;
the captured, staged and transferred hashes agree. The panel reports Uploaded
and the saved-upload dialog shows one imported image. Discard cancellation
preserves the capture. Confirmed discard removes only its private directory,
leaving the imported upload record and separately staged bytes intact. Native
viewport selection and zoom work after the dialogs close.

![Film shows the completed upload without automatically associating a task](../images/film-capture-uploaded.png)

The run exits cleanly, removes its disposable profile and leaves the normal
profile unchanged. This proves bounded still-capture interaction and synthetic
upload handoff. Desktop video cancellation, sustained GPU/audio, human motion
review, live uploads, other OS/DPI combinations, finishing/export and integrated
release acceptance remain separate.

### Film timeline controls

The **Timeline** child panel offers **Build timeline**. Its confirmation lists
the editorial frame count/rate and a local scene choice for each recipe shot.
Missing choices explain that the shot must be built first. The dialog explains
that it creates a new sequence, keeps the working scene selected and references
live scenes whose later edits affect the timeline. Cancel creates no review.
The confirmed selection uses the same session command as local MCP. Build is
disabled outside Object Mode in a Blender window, while MCP preparation remains
available in Edit Mode.

Known rollback errors remain readable and copyable. Incomplete cleanup hides
the build action and requires **Discard timeline review** with its inspection
checkbox; this never deletes Blender data. Dismissed reviews no longer show
their status or Copy error action in the panel; MCP can still inspect the saved
review error. Ordinary status matches the current production and recipe; a
reload hides prior built/error status without hiding unresolved partial cleanup.
Drawing only reads cached status.
Native source/destination guards and single-use approval have synthetic installed
coverage. Exact ZIP SHA-256
`aef03c55e607a3ea99eb839bd4cdef2cc4c7e6517aa5ca5152d302744874f402`
passes 869 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.

Desktop interaction with that same ZIP passes on macOS arm64 Blender 5.1.2 in
an isolated profile. The local fixture supplies two recipe shots and a second
take for one shot, with external Python sockets blocked. Native mouse input
opens the panel and confirmation, which displays 180 frames at 30 fps. Selecting
the nondefault scene for the second shot and pressing Escape leaves every scene
and saved job unchanged and creates no review. A fresh dialog accepts the same explicit scene
choice, and Return confirms the build.

![Timeline approval shows the frame count and an explicit choice between takes](../images/film-timeline-approval.png)

Exactly one new timeline contains the selected shots at frames 1–120 and 121–180,
with the working scene still selected and its objects intact. Saved jobs and
application receipts are unchanged. Edit > Undo removes only the new timeline;
Edit > Redo restores the exact scene sources and frame boundaries. The consumed
review stays consumed. After history invalidates its scene handle, the panel
requires a fresh approval for another build.

![Film reports the built timeline while preserving the working scene](../images/film-timeline-built.png)

Viewport Light selection and Home framing work after the dialogs. The native
scene selector opens the built timeline. Selecting that scene in the Video
Sequencer's own scene selector displays the two editable scene strips.

![The Video Sequencer displays the selected 120-frame and 60-frame shots](../images/film-timeline-sequencer.png)

The run records zero service requests and downloads, exits cleanly, removes its
disposable profile and leaves the normal profile unchanged. This establishes the
synthetic timeline interaction, not live provider compatibility, human motion/audio
review, other OS/DPI combinations, capture/finishing/export or release acceptance.

Review follow-up ZIP SHA-256
`c008687d12a1dc370e841e0daf34abade5d7960d3bbf1458ecb03bca929eba20`
passes 958 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.
A fresh isolated desktop check on Blender 5.1.2 supplies a synthetic incomplete
cleanup. Mouse input opens **Discard timeline review**, checks the inspection
acknowledgement and Return confirms dismissal. The old error and Copy error
control disappear, while explicit MCP inspection retains the discarded error.
Dismissal preserves existing scene data, including the partial fixture scene,
and saved jobs.

![An uncertain timeline review offers inspection and dismissal](../images/film-timeline-error-before-dismissal.png)

![Dismissal clears the old error and restores the build control](../images/film-timeline-error-dismissed.png)

Viewport selection and Tab enter Edit Mode, where **Build timeline** is visibly
disabled. A main-thread probe of the shared command still prepares a ready
review; approval rejects Object Mode absence without consuming it or building.

![Edit Mode disables building while read-only preparation remains available](../images/film-timeline-edit-mode.png)

This follow-up records zero service requests/downloads, clean exit, disposable
profile cleanup and an unchanged normal profile. Its physical evidence covers
dismissal, viewport focus and Edit Mode gating; it does not repeat the earlier
build, Undo/Redo, missing-choice or Sequencer journeys.

Recipe-status validation uses exact ZIP SHA-256
`eea65caf46764ed36dae6717c5339da472127d668b389f0564e156c9b8024bc8`,
with 960 installed tests passing on each macOS arm64 Blender 5.0.1, 5.1.2 and
5.2.1. The isolated 5.1.2 desktop fixture displays a built timeline, then calls
the MCP recipe-load handler on the main thread with a replacement recipe. The
old Built label disappears; the prior review and scene data remain inspectable.
Viewport selection and Home framing work. A synthetic incomplete cleanup stays
visible and blocks preparation across another recipe reload. Mouse input opens
its discard dialog, checks inspection and Return dismisses it, clearing the panel.

![Reloading a recipe removes the prior timeline confirmation](../images/film-timeline-recipe-reloaded.png)

Saved jobs remain unchanged, with zero service requests/downloads, clean exit,
disposable-profile cleanup and normal-profile preservation. This check covers
recipe-status filtering and retained uncertainty, not a new build/Undo journey
or the native recipe file chooser.

### Film composition controls

The **Composition** child panel uses equal Final/Previs segments, then **Prepare
composition**, **Request price** and a separate **Generate** confirmation. The
confirmation shows the original scene, timing, source/layer counts and full exact
CU cost. Discard requires confirmation; cancellation affects only preparation or
the pending price. Saved jobs remain available after either action. Error details
wrap the complete cached error and support copying. Drawing only reads cached
status; the existing runtime maintenance owns progress.

Installed synthetic tests exercise native operator execution/dialog construction,
MCP parity and read-only drawing. The corrected navigation implementation passes
916 installed tests on each of Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64.

Final/Previs is temporary WindowManager UI state, shared across the current
Blender session and excluded from saved scene data. Native edits to a scene-owned
custom property tag its owning scene, which invalidated retained quotes even
though the recipe was unchanged. Direct Python assignment in the earlier
regression did not reproduce that native update. The corrected installed
regression also tags the property's owner, preserving the same quote without
service requests after navigation. Frame changes still invalidate the captured
scene revision; that guard is unchanged.

An isolated macOS arm64 Blender 5.1.2 desktop check installed exact ZIP SHA-256
`6f932e81a802f8569378c38ad3d4b820da779a1f86090272585c9b1db8e1335f`.
All 136 packaged Python files matched the reviewed source. Native input cancelled
preparation, cancelled and confirmed discard, prepared a fresh review and requested
its exact synthetic price. Final → Previs → Final preserved the same review,
quote, scene and request count. Editing the current frame invalidated the review
without another request; the full error was readable in its details dialog.

The separate Generate confirmation displayed the original destination, 120 frames
at 30 fps, one source/layer and full synthetic price `0.10000000000000001` CU.
Cancelling preserved the quote with no submission. Confirming created exactly one
mocked durable master; discarding its review preserved that job, visible through
**Inspect saved jobs**. Viewport selection and zoom worked after leaving the
controls. Recipe and source bytes stayed unchanged. The process exited cleanly,
removed its disposable profile and left the normal profile unchanged.

![Film composition confirmation showing exact price before mocked submission](../images/film-composition-approval.png)
![Saved Film composition job after discarding its review](../images/film-composition-saved.png)

SDK transport and media metadata were mocked, and external socket/DNS calls were
disabled. This proves the scoped native interaction flow, not real media probing,
live provider quality, other OS/DPI behavior, local final assembly/export or
complete Film/release acceptance.

### Film review controls

The **Review** child panel follows Composition. It uses equal Final/Previs
segments, then an **Assemble review** box with a `SEQUENCE` header icon.
**Prepare review** opens a dialog naming the recipe scene and mode. **Include saved
master as muted alternate** is enabled only when a saved master video exists.
The dialog states the 2 GiB private copy limit and the installed `ffprobe`
requirement, and that nothing is downloaded, uploaded or generated. Cancelling it
creates no review. A saved-job storage error while checking the master reports its
storage message rather than asking for a valid recipe.

A ready review shows its frames, fps and shot/source counts, then **Build review
scene**. That separate confirmation names the recipe scene, mode, timing, counts,
private copy size and master inclusion. It states that the build creates a new
scene, keeps the working scene selected and marks generated sources applied, and
that Undo removes only the scene. Build is disabled outside Object Mode with a poll
message. Like the timeline build, the build operator declares only Blender's Undo
option, without the register option behind the redo panel and the Info operator
log. Preparing and ready reviews add "Selecting, editing or Undo here discards
it": object selection or edits and any Undo or Redo invalidate an unbuilt review
and delete its copies. Preparing and waiting reviews show a status line with
**Cancel preparation**; stopping and building show status only. The waiting line
says the scene was left and that reselecting it needs a new preparation: selecting the
recipe scene again invalidates its unbuilt reviews and deletes their copies. Ready,
failed and cancelled reviews offer **Discard review** with confirmation. Uncertain
builds hide preparation and offer **Save review receipt** or **Acknowledge
inspection** (with its checkbox), plus **Inspect saved jobs**. **Error details**
wraps the complete error and offers copying. Drawing reads cached status only; the
maintenance pump owns progress. Studio's Film page adds a sixth **Review** tab,
drawn as two rows of three at narrow widths.

Installed synthetic tests cover operator execution, dialog construction including
the enabled master option for a saved master, dismissed dialogs, a storage error
in the preparation dialog, readable full-queue admission, the warning line on
preparing and ready reviews with selection and Undo/Redo-handler invalidation, a
real `window.scene` round trip, a previs build beside a ready final review, MCP
parity, read-only panel and Studio drawing, mode navigation, Edit Mode gating and
the build operator's options. Physical desktop interaction, screenshots and other
OS/DPI behavior for these controls have not been captured; that evidence is pending.

### Film export controls

The **Export** child panel follows Review, and Studio's Film **Review** tab draws
it below the review controls after a separator. It holds one **Export video** box
with a `FILE_MOVIE` header icon. Without a current export it shows **Export
video...** with two lines: it renders a built review scene to a new MP4, in an
offline Blender process that never overwrites. That action opens Blender's file
browser at the Output Folder's Film subfolder with a suggested portable name. The
browser's side panel shows a list of the recipe's review scenes (an `ERROR` icon
marks a blocked one, with its reason wrapped below), frames and rate, scene size,
media count and whether sound strips are audible. It offers **Audio** (Match sound
strips, Include or None), **Use review scene size** with Width and Height enabled
only when it is off, and the lines "Nothing renders yet." and "Render video asks
again." A scene size outside 64 to 4096 pixels adds an `INFO` line "Outside 64 to
4096 pixels; set an export size", and the browser opens with the option off and
the nearest bounded size. Its confirm button reads **Choose video file**.

A ready export lists the review scene and mode, frames and rate, the destination
file name and "Selecting, editing or Undo here discards it", then **Render video**
and **Discard export**. **Render video** opens a separate confirmation with the
review scene, timing and size, codec and audio track, media count, the full
wrapped destination, "Renders in an offline Blender process; never overwrites a
file.", that the working file and scenes stay unchanged and no credits are spent,
and which verification runs. It is unavailable outside Object Mode, with a poll
message. A running export shows its stage with a `TIME` icon (for example
"Rendering 24/48 frames (50%)") and **Cancel export** with confirmation; stopping
shows status only. A failed save shows "Video verified but not saved", **Choose
new file...** (a file browser), then **Save video copy** (a confirmation of the
exact new file) and **Discard export**. An exported video shows its name with a
`CHECKMARK`, then a row with **Open folder** and **Copy SHA-256**, **Export
video...** again and **Discard private files**. Errors add **Error details**,
which wraps the complete error and offers copying. Drawing reads cached status
only; runtime maintenance owns progress and redraws the sidebar when it changes.

Installed synthetic tests cover the file browser invoke and side panel, dismissal,
numbered suggestions, explicit audio and size choices, the Render dialog and its
inert dismissal, the failed-save copy dialogs, the panel's ready, running and
exported states, read-only panel and Studio drawing and Edit Mode gating. Physical
desktop interaction, screenshots and other OS/DPI behavior for these controls have
not been captured; that evidence is pending.

### Film case-study controls

The **Case study** child panel follows Export, and Studio's Film **Review** tab
draws it below the export controls after a separator. It holds one **Case-study
bundle** box with a `PACKAGE` header icon. Without a current case study it shows
**Export case study...** with two lines: it packs a review, timeline, media,
recipe and ledger into a new ZIP and never overwrites. That action opens Blender's
file browser at the Output Folder's Film subfolder with a suggested portable
`<Title> - Case Study.zip`. The browser's side panel lists the recipe's review
scenes (an `ERROR` icon marks a blocked one, with its reason wrapped below), the
chosen scene's frames and rate and media count, then **Include director
timeline** with a list of timelines and their shot counts (disabled when the
checkbox is off), or "No director timeline", and the lines "Nothing is written
yet." and "Save case study asks again." Its confirm button reads **Choose
case-study file**.

A ready case study lists the review scene and mode, the timeline or "No director
timeline", the scene and media counts with their size, the destination file name
and "Selecting, editing or Undo here discards it", then **Save case study** and
**Discard case study**. **Save case study** opens a separate confirmation with the
review scene, timeline and shot count, contents, a ledger line such as "Ledger: 1
approved task; 1 CU quoted for 1 task" (CU in the shared display format), the full
wrapped destination, "Builds in offline Blender processes; never overwrites a
file.", that the working file and scenes stay unchanged and no credits are spent,
and that the documents omit credentials, URLs, service IDs and local paths. It is
unavailable outside Object Mode, with a poll message. A running case study shows
its stage with a `TIME` icon (for example "Packing the archive (50%)") and
**Cancel case study** with confirmation. A failed save shows "Case study verified
but not saved", **Choose new file...**, then **Save case-study copy** and
**Discard case study**. A saved archive shows its name with a `CHECKMARK`, a row
with **Open folder** and **Copy SHA-256**, **Export case study...** again and
**Discard private files**. Errors add **Error details**. Counts use correct
singular and plural forms. Drawing reads cached status only; runtime maintenance
owns progress.

Installed synthetic tests cover the file browser invoke and side panel, numbered
suggestions, the Save dialog text and its inert dismissal, the failed-save copy
dialogs, progress, the panel's ready, running and saved states, read-only panel
and Studio drawing and Edit Mode gating. Physical desktop interaction, screenshots
and other OS/DPI behavior for these controls have not been captured; that
evidence is pending.
