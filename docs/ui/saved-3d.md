# Saved 3D results

Interaction rules and desktop evidence for saved models, splats and mesh edits. The shared rules are in the [UI style guide](../UI_STYLE.md).

## Saved static model confirmation

Show one import control for each supported GLB result, labelled as in
[Saved model package review](#saved-model-package-review). The confirmation
names the selected scene and cursor coordinates, states that it adds one model
group with packed textures, preserves existing objects/selection, and excludes
external-file GLBs. A changed cursor or scene requires fresh
approval. Drawing only reads prepared values.

The screenshot and acceptance below predate saved package import and show the
earlier wording. The current controls are described in
[Saved model package review](#saved-model-package-review).

![Native static model confirmation shows the selected scene cursor and supported import limits](../images/saved-model-approval.png)

Offline desktop acceptance on macOS arm64 Blender 5.1.2 used the exact ZIP
`bac52e333078c09bc1581e5a530dac67a749d94c179b230a3d0ace7b2afb410f`. Mouse confirmation imported one textured
triangle hierarchy into one new group at cursor (3, 0, 0), without another mock
generation or request. Existing selection stayed intact. Viewport clicking,
front-view keyboard input and zoom worked after import. Blender exited cleanly
and the normal-profile fingerprint was unchanged. The test-only app copy used
a distinct bundle identifier and local ad-hoc signature for window targeting,
with vendor executable code and the extension ZIP unchanged. Synthetic tests
and desktop evidence do not establish paid provider acceptance, rig/animation or
in-place editing, other OS desktop behavior, release readiness or #263 resolution.

## Saved model package review

Each importable unit of a saved job gets one control from the shared
descriptors: **Import <format> model (N)** for the primary unit and
**Import alternate: <format> (N)** for the others, in classified order, with
GLB, glTF, FBX, OBJ or PLY as the format and N counting every saved file. Splat
units use their own labels (see [Saved splat review](#saved-splat-review)); an
unsupported model is not drawn. The 480 px review adds a **Selected**
line naming the saved files and whether they are the primary or an alternate
result (for example `Selected: OBJ + MTL + 1 map (alternate result)`), then the
cursor, the new group, packed textures and preserved selection. Format lines
follow: GLB and glTF keep scene FPS and the timeline, FBX packs embedded textures,
rejects external texture files and keeps the file's clip timing, OBJ leaves out
maps that were not saved, and PLY says a file without splat data imports as a
mesh. A last line says the files are checked again first. Every line stays within 66 characters, the longest line
the earlier 480 px desktop capture showed. Drawing only reads the prepared
values; cancel discards the approval.

Installed native tests on macOS arm64 Blender 5.1.2 check the labels drawn for a
job with a GLB alias and an OBJ package, the review lines, read-only drawing and
cancel. Physical desktop evidence of this dialog, its fit at other sizes and DPI,
and viewport interaction after a non-GLB import is pending.

## Saved splat review

SPZ and `.splat` units are drawn as **Import splats: SPZ (N)** or
**Import splats: .splat (N)** for the primary unit and
**Import alternate splats: <format> (N)** otherwise. A PLY keeps the model label,
because only its bytes decide between a mesh and splats. The same 480 px review
names the selected file and the cursor (**Place splats bottom at cursor** for SPZ
and `.splat`), says the import makes a new group with its own new material, and
for SPZ that versions other than 2 and 3 stop unchanged. SPZ, `.splat` and PLY
reviews then draw two dropdowns, **Points** (250,000, 500,000, 1,000,000 or
2,000,000) and **Saved axes** (**OpenGL: Y up** or **OpenCV: Y down**), and
three lines: splats show as coloured points because Blender has no splat
renderer, denser files are thinned evenly, and the default axes follow the file
format so the result should be checked upright. Invoke sets the dropdowns from
the prepared approval's defaults. Changing one calls `check()`, which exchanges
the approval for a new handle with the same scene, cursor and unit; a changed
destination shows an error line instead, and confirmation fails closed. A
refusal at confirmation, such as a busy local render, is reported with its
reason after **Model import was not started:**. Drawing only reads prepared
values, every line stays within 66 characters, and cancel discards the current
handle.

After an import, the job row adds status lines from the session summary:
**Shown as points: K of N splats** and, when an SPZ declares extensions,
**This SPZ declares extensions; check its axes**. They disappear when undo
history changes.

Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 check the
labels, the review lines and dropdowns, read-only drawing, option revision under a new handle, the
old handle's refusal, confirmation, the busy-slot refusal reason and cancel.
Physical desktop evidence of the dropdowns, the dialog fit at other sizes and
DPI, the post-import status lines, and viewport navigation after a
1,000,000-point import is pending.

## Saved mesh edit review

**Apply mesh edit (N)** names the captured scene, source mesh and selected saved
GLB. The dialog shows the replacement policy, scene/local coordinate placement
and Keep original choice before confirmation. Explain geometry/UV/material
replacement, exact-topology UV/retexture restrictions, no automatic fitting, preserved
object context and the dependence of undo on Blender settings. Defaults keep an
original copy. Explain that history changes affect the scene only, not saved jobs
or spending.

Option changes use `check()`, outside drawing, and revise the existing captured
approval instead of selecting a new target. A stale target or scene requires
cancellation and fresh review. `draw()` only reads the prepared labels and
operator properties. Completed-result reviews retain the reuse notice.

Mirrored or zero-scale source transforms cannot use scene-coordinate mapping.
The native dialog opens with **Object local coordinates** and a visible
explanation for those sources. Review and confirmation remain explicit; choosing
the unsupported scene-coordinate option cannot start verification or application.
For **Apply to captured source**, inspect the retained source's transform before
choosing that default. A different selected object's transform must not affect it.

A captured-source follow-up on macOS arm64 Blender 5.1.2 uses ZIP SHA-256
`03074fe0f5ff70e360e392502a14064f36312dd463058866edeeee58077c541e`,
which passes 719 native tests on each supported Blender series. With another
positive-scale mesh selected, mouse input opens the mirrored captured mesh's
review with object-local coordinates and its explanation. Escape preserves both
meshes and the saved job; Return applies only to the captured mesh, retaining
its negative scale and Keep original copy. Native Edit > Undo/Redo restores the
source and copy without changing durable job state or request counts. Viewport
selection, front-view keyboard input and zoom work after the dialogs. The
synthetic transport makes no additional service requests or submissions during
review, application or history changes. The isolated run exits cleanly, removes
its profile and leaves the normal profile unchanged. Zero-scale and reversed
selection cases have native regression coverage; other OS desktop and live
provider acceptance remain separate.

![Captured mirrored mesh approval uses local coordinates while another mesh remains selected](../images/captured-mirrored-mesh-approval.png)

An isolated macOS arm64 Blender 5.1.2 desktop check used ZIP
`21edce46cf2c0e94095ba27668c2acef3b6b68968dc0dc0082921f1bd0760000`,
which passes 670 installed native tests on each of Blender 5.0.1, 5.1.2 and 5.2.1.
The mirrored-source dialog opened with local coordinates selected. Escape
cancelled; selecting scene coordinates showed rejection, and returning to local
coordinates allowed Return confirmation. Source scale remained negative, Keep
original retained a copy, and a second explicit reuse persisted `mesh_edit`
without more mock requests or submissions. Viewport selection, front-view input
and zoom worked. Blender exited cleanly with the normal profile unchanged.
The test app used a distinct local bundle identity with unchanged vendor
executable code. This synthetic check does not establish provider alignment,
other OS desktop behavior, global undo or release acceptance.

![Selected mirrored source with negative scale before saved mesh application](../images/mirrored-mesh-before.png)

![Mirrored source approval selects and explains local coordinates](../images/mirrored-mesh-approval.png)

![Applied mirrored mesh retains its negative source scale](../images/mirrored-mesh-result.png)

Offline desktop acceptance on macOS arm64 Blender 5.1.2 used final ZIP
`e1eed465de2c9376231e54a7e623f1391974f4102ba54f2845fddbec369dda38`,
which passes 659 full native tests each on Blender 5.0.1, 5.1.2 and 5.2.1.
Mouse input opened the explicit source review. Escape cancelled without applying;
viewport selection and front-view keyboard input then worked. A fresh review
named the selected source, and Return confirmed geometry replacement with Keep
original enabled. The source became the synthetic three-vertex result, its
original copy remained, and the durable job became applied without another mock
submission or request. The temporary message acknowledges approval rather than
continuing to describe verification after it has already finished.

The preceding desktop check used ZIP
`cc603cfa3c98e29430d5ea72c2c54a1ce6f7480324695c158d460f5f437e42f0`;
the only subsequent production change was that message text. It additionally
verified both policy and coordinate menus, Keep original toggling, cancellation,
viewport focus after application and explicit completed-result reuse confirmed
with Return. Reuse preserved the completed generation and recorded one separate
applied local claim without another mock request or submission.

Both isolated Blender processes exited cleanly and their normal-profile
fingerprints were unchanged. The test-only app copy had a distinct bundle ID and
local ad-hoc signature; vendor executable code and extension ZIP were unchanged.
The fixture freezes catalog loading and mocks service responses; its loading
labels are not live connection evidence. These checks do not establish provider
alignment, pre-generation source binding, remaining edit policies,
other OS desktop behavior, #263 resolution or release acceptance.

[Before application](../images/saved-mesh-edit-before.png),
[approved replacement result](../images/saved-mesh-edit-result.png).

![Native mesh approval identifies the source and replacement policy](../images/saved-mesh-edit-approval.png)


## Captured mesh source interaction evidence

The saved-job **Apply to captured source (N)** action opens the existing mesh
review with the original exported object, independently of active selection.
Its extra line identifies the unchanged captured source. **Apply mesh edit (N)**
keeps explicit current-destination review; both require confirmation.

On macOS arm64 Blender 5.1.2, an isolated installation of ZIP SHA-256
`f9f57e8efd3679bf8143713067e938eb4545d433ff5e27cc349a938a61fac976`
was exercised with synthetic transport and a real source export. With another
mesh active, mouse activation named `Cube.001` as the captured source. Escape
canceled without changing the saved ready record or either mesh; viewport focus
and numpad front view still worked. Reopening and confirming with Return replaced
the source's eight vertices with the saved three-vertex fixture, retained an
original copy, and left the other active mesh at eight vertices. The job became
applied with no additional mock submission, service request or download. The
normal Blender profile was unchanged and the isolated process exited cleanly.

![Captured source confirmation names the exported cube while another mesh remains active](../images/captured-mesh-source-approval.png)

![Applied captured source retains its original copy and leaves the other active mesh unchanged](../images/captured-mesh-source-result.png)

The same interaction was repeated with the integrated export/quote changes on
macOS arm64 Blender 5.1.2 using ZIP SHA-256
`a2254eb9ae5b24608eacf1e850dbbb95d9a1e4ff7b6b4b881bd4de2ef5e56610`.
Mouse activation again identified the exported source despite a different active
mesh. Escape preserved the ready job and both meshes; viewport focus and numpad
front view remained usable. Return applied the three-vertex result to the source,
kept its original copy and left the other mesh at eight vertices. Mock request,
submission and download counts stayed unchanged through application; a socket
guard recorded no network attempts. Installed bytes were verified before and
after the run, the normal profile was unchanged, and the process exited cleanly.
The images above remain captures from the earlier named artifact.

This proves the local source-selection, cancellation and confirmation interaction.
The synthetic form's pending estimate is not live pricing evidence. It does not
establish provider alignment, other OS desktop behavior, #263 resolution, remaining
edit policies or release acceptance. See
[the source contract](../MESH_APPLICATION.md#applying-to-the-captured-mesh-source).


## Retexture review

The mesh review's **Replace textures** choice preserves geometry and adopts all
result UV layers and mesh material assignments. Its two explanation lines name
that replacement and require exactly matching indexed topology and positions.
Keep original and coordinate placement remain explicit, and drawing stays read-only.
Both current-destination and captured-source review use this policy.

Offline interaction on macOS arm64 Blender 5.1.2 used exact ZIP
`53587fc3756f6eb9acaa40df066b0fc8dc80defb5a009059ec3148f5ecf54b61`,
which passed 683 installed tests on each of Blender 5.0.1, 5.1.2 and 5.2.1.
Mouse selection exposed the new policy and its geometry-preservation explanation.
Escape canceled without changing materials, geometry or local claims. A fresh
review selected the policy using the native menu and keyboard; Return applied
it with Keep original enabled. Vertex positions stayed identical, the saved
material replaced the fixture's blue material, and one separate local claim
became applied while the completed generation stayed applied. Mock submissions
and requests remained unchanged. Viewport click, front-view and orbit keys,
Outliner selection and zoom worked. The isolated process exited cleanly and the
normal profile was unchanged. The test-only application identifier/signature
changed for window targeting; executable code and extension ZIP were unchanged.

The fixture uses synthetic transport and pauses catalog loading. These images
are local interaction evidence, not live pricing or provider appearance quality.
Provider indexing/alignment, other OS desktop behavior, #263 and
full release acceptance remain unverified.

[Before retexture](../images/saved-retexture-before.png),
[applied retexture with original retained](../images/saved-retexture-result.png).

![Retexture review explicitly preserves geometry and requires matching topology](../images/saved-retexture-approval.png)


## Saved mesh undo interaction

The approval dialog explains that Keep original retains an unselected copy,
Blender settings control undo, and history changes leave jobs and spending
recorded. The shared command uses native history for all three mesh policies;
see [the contract](../MESH_APPLICATION.md#native-undo-for-saved-mesh-edits).

An isolated macOS arm64 Blender 5.1.2 desktop check used exact ZIP SHA-256
`0d0a8da1ff9667e2bf7ea289f4e73ec01183ecb0268bddc81d50305b8308c862`.
The same ZIP passed 688 installed tests on each of Blender 5.0.1, 5.1.2 and 5.2.1.
Mouse input opened captured-source review while another mesh was selected, and
Return confirmed. The source changed from eight to three vertices with its
original copy retained; the other mesh stayed at eight vertices. Edit > Undo
restored the eight-vertex source and removed the copy. Edit > Redo restored the
three-vertex result and its copy. The saved job stayed applied and mock submission
and request counts stayed unchanged throughout. Viewport zoom and front-view
keyboard input worked after Redo. The isolated process exited cleanly and the
normal profile fingerprint was unchanged.

This is synthetic local interaction evidence, not live pricing/provider output,
other OS desktop acceptance, resolution of #263 or complete release acceptance.
The fixture pauses catalog loading. Its test-only application identifier and
signature differ for window targeting; executable code and extension ZIP do not.

After review, ZIP `3f36db535d94416bdf351b086a1356ea1993fb1d4c482c1d7759275a32e0e072`
passed 689 installed tests on all three versions. A fresh isolated 5.1.2 desktop
run repeated approval, menu Undo/Redo and viewport input. Public job status
remained readable throughout; `mesh_edit` became null on Undo and remained null
after Redo instead of following recreated objects by name. Geometry and original
copy restoration still worked, with unchanged durable job and mock request
counts. The process exited cleanly and the normal profile was unchanged. The
screenshots below show the preceding identical UI; the follow-up changes only
transient status ownership and adds a failed-import history regression.
A final receipt-recovery guard keeps that status retired even when saving a
pending success receipt after Undo; it changes no native UI or scene application.
Its exact ZIP and full matrix validation are recorded in the PR.

[Undo restores the source](../images/saved-mesh-undone.png),
[Redo restores the edit](../images/saved-mesh-redone.png).

![Mesh approval explains native undo and unchanged job records](../images/saved-mesh-undo-approval.png)


## Parts application interaction

The saved-mesh review offers **Replace with parts** as an explicit policy. Its
read-only explanation identifies the source, empty mesh parent, named children,
2-to-128 part limit, unchanged source context and Keep original behavior. It
states that every mesh in the chosen GLB is treated as a part. It does not infer
variants or automatically fit the result. The shared UI/MCP command applies the
[parts contract](../MESH_APPLICATION.md#apply-static-parts).

An isolated macOS arm64 Blender 5.1.2 desktop run installed the exact ZIP with
SHA-256 `ad88e5b70dcf879d182a4805415dcb0ecab114d32a7287e711b84923f6f86be7`.
Native clicks and keyboard input selected the policy, cancelled without mutation,
then confirmed application to the captured source while another mesh remained
selected. The source became an empty mesh parent with two named triangle parts;
Keep original retained its eight-vertex copy and the other mesh kept eight
vertices. Edit > Undo restored the eight-vertex source and removed the parts and
copy. Edit > Redo restored both children and the copy. The public job stayed
applied, transient mesh status retired on undo, and mock submission/request
counts did not change. Viewport zoom/front-view input and Outliner expansion
remained usable. The owned test process exited cleanly and the normal profile
was unchanged.

Transport and result geometry were synthetic; the frozen model/estimate labels
in the screenshots are fixture state, not live provider or estimate performance
evidence. This proves the scoped local interaction, not provider alignment,
other-platform desktop behavior or integrated release acceptance.

[Applied parts and preserved selection](../images/saved-mesh-parts-applied.png).

![Parts approval names the target and explains grouping](../images/saved-mesh-parts-approval.png)

The error-message update's ZIP
`b5e207c2bd571e89e31e45e1dce24a43fd341ba1f23766bc2792e4be6445eb9c`
passed 700 installed tests on each supported Blender version on macOS arm64.
In an isolated 5.1.2 desktop check, confirming single-mesh replacement with a
two-mesh fixture failed without changing either source or selection. **Job needs
review** opened the full message identifying the saved GLB, source and edit policy.
Escape closed it and front-view keyboard input worked in the viewport. Mock
submissions, requests and downloads stayed unchanged, with no network attempts.
The process exited cleanly, its profile was removed and the normal profile was
unchanged. Earlier screenshots retain their original artifact provenance.

## Animated model import interaction

The shared saved-result button was **Import model** in this capture; it is now
named by format, as in [Saved model package review](#saved-model-package-review).
Its review names the scene
and cursor and explains a new group, packed textures, preserved selection,
retained rigs/clips and unchanged timeline. Drawing remains read-only. The
[import contract](../MESH_APPLICATION.md#rigged-and-animated-model-import) describes
clip timing, staging isolation and the separate in-place transfer boundary.

The exact ZIP with SHA-256
`ee5dc51cd853739685458c589975aca6acf326c460dd9e12eefecb4e74ec0adf`
passed 705 installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.
An isolated 5.1.2 desktop check opened the review, cancelled without importing,
then confirmed a new character with two bones and two clips. The original cube
remained active. Native viewport zoom/front-view input and Outliner expansion
worked. Clicking frame 30 on the timeline animated the rig and skinned/morphed
triangle from its frame-zero state; evaluated vertices moved two units in X and
one unit through the morph. FPS stayed 30 and the range stayed 1 through 90.
The saved job stayed applied and mock submission/request counts stayed unchanged.
The completed test exited cleanly with the normal profile fingerprint unchanged.

Transport and geometry were synthetic. Frozen catalog/estimate labels in these
screenshots are fixture state, not live performance evidence. This scoped check
does not establish provider rig compatibility, in-place retargeting, other OS
desktop acceptance or integrated release acceptance. An earlier interrupted test
exit crashed in the fixture's temporary-preference cleanup during Python
finalization; the completed repeat used explicit fixture cleanup before quitting.

[Frame zero](../images/saved-model-animation-start.png),
[frame thirty](../images/saved-model-animation-end.png).

![Model import approval explains retained rigs, clips and timeline behavior](../images/saved-model-animation-approval.png)

## Rig attachment interaction

The saved-mesh review offers **Attach rig**. It names the captured source and
explains matching geometry, retained source UVs/materials, bone weights and clips,
Keep original and native undo. It also explains that the source and new rig group
must move together afterward. Drawing stays read-only; the shared UI/MCP command
implements the [skin attachment contract](../MESH_APPLICATION.md#attach-a-returned-rig).

The final ZIP with SHA-256
`43d303619c6eb4d0ebf9e6bad2dd40f210f4cce0890587a8bade647326264a2b`
passed 715 installed tests each on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1.
Isolated 5.1.2 desktop input selected Attach rig, cancelled without mutation and
confirmed against the captured triangle while another mesh stayed selected.
The source retained its geometry, gained two bone groups and an armature modifier,
and Keep original retained an unselected copy. Native Edit > Undo removed the
rig, groups and copy; Redo restored them. The saved job stayed applied and its
transient mesh status retired on undo. Mock submission/request counts stayed
unchanged. Viewport zoom/front-view input and Outliner expansion worked; clicking
frame 30 moved the skinned source two units in X while the original stayed still.
The completed repeat exited through explicit fixture cleanup and verified that
the normal profile remained unchanged.

Transport and geometry were synthetic. Frozen catalog, estimate and price labels
are fixture state, not live pricing or performance evidence. This check does not
establish provider compatibility, existing-rig retargeting, other OS desktop
acceptance or integrated release acceptance. An earlier interrupted exit crashed
in the fixture's temporary-preference cleanup during Python finalization; its
interaction observations were repeated before a clean exit.

The screenshots and cancellation/selection sequence used the preceding ZIP
`8623714355635f3d3f2a36539992161547add46ed462910086f4f33e71c91fd5`.
The final ZIP differs only by formatting in one Python member (identical AST);
attachment, native undo/redo and frame-30 deformation were repeated on that final
ZIP, followed by a clean exit and unchanged normal-profile fingerprint.

[Animated source, original copy and preserved selection](../images/saved-mesh-rig-animated.png).

![Rig approval names the captured source and explains compatibility](../images/saved-mesh-rig-approval.png)
