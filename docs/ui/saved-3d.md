# Saved 3D results

Interaction rules and desktop evidence for saved models, splats and mesh edits.
The shared rules are in the [UI style guide](../UI_STYLE.md). The desktop checks
below used an isolated installed package on macOS with synthetic transport;
their catalog, estimate and price labels are fixture state. They do not
establish provider output, live pricing or other platforms.

## Saved static model confirmation

Show one import control for each supported GLB result, labelled as in
[Saved model package review](#saved-model-package-review). The confirmation
names the selected scene and cursor coordinates, states that it adds one model
group with packed textures, preserves existing objects/selection, and excludes
external-file GLBs. A changed cursor or scene requires fresh
approval. Drawing only reads prepared values.

The screenshot and desktop check below predate saved package import and show the
earlier wording.

![Native static model confirmation shows the selected scene cursor and supported import limits](../images/saved-model-approval.png)

Mouse confirmation imported one textured triangle hierarchy into one new group at
cursor (3, 0, 0), without another mock generation or request. Existing selection
stayed intact, and viewport clicking, front-view keyboard input and zoom worked
after import.

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
mesh. A last line says the files are checked again first. Every line stays
within 66 characters, the longest line the earlier 480 px desktop capture
showed. Drawing only reads the prepared values; cancel discards the approval.

Physical desktop evidence of this dialog, its fit at other sizes and DPI,
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

Physical desktop evidence of the dropdowns, the dialog fit at other sizes and
DPI, the post-import status lines, and viewport navigation after a
1,000,000-point import is pending.

## Saved mesh edit review

**Apply mesh edit (N)** names the captured scene, source mesh and selected saved
GLB, followed by **(primary result)** or **(alternate result)**. A GLB that is
not the job's primary result is drawn as **Apply alternate mesh edit: GLB (N)**
or **Apply alternate to captured source: GLB (N)**, mirroring its import label.
The dialog shows the replacement policy, scene/local coordinate placement and
Keep original choice before confirmation. Invoke starts the policy from the
prepared approval, and a line under it reads **Default edit follows this job's
Retexture task.** (with the job's task), **This mesh has no rig, so the Animate
result starts on Attach rig.** (an Animate job and an unskinned mesh), **This
mesh already has a rig, so the edit starts on Attach rig.** (a skinned source)
or **Default edit is not from this job's task; check it.** Explain
geometry/UV/material replacement, exact-topology UV/retexture restrictions, no
automatic fitting, preserved object context and the dependence of undo on
Blender settings. Defaults keep an original copy. Explain that history changes
affect the scene only, not saved jobs or spending. After confirmation, the
temporary message acknowledges approval rather than describing verification that
may already have finished.

Option changes use `check()`, outside drawing, and revise the existing captured
approval instead of selecting a new target. Physical desktop evidence of the
default-edit line and the alternate labels is pending. A stale target or scene
requires cancellation and fresh review. `draw()` only reads the prepared labels
and operator properties. Completed-result reviews retain the reuse notice.

Mirrored or zero-scale source transforms cannot use scene-coordinate mapping.
The native dialog opens with **Object local coordinates** and a visible
explanation for those sources. Review and confirmation remain explicit; choosing
the unsupported scene-coordinate option cannot start verification or application.
For **Apply to captured source**, inspect the retained source's transform before
choosing that default. A different selected object's transform must not affect it.

With another positive-scale mesh selected, mouse input opened the mirrored
captured mesh's review with object-local coordinates and its explanation. Escape
preserved both meshes and the saved job; Return applied only to the captured
mesh, retaining its negative scale and Keep original copy. Native Edit >
Undo/Redo restored the source and copy without changing durable job state or
request counts. Viewport selection, front-view keyboard input and zoom worked
after the dialogs.

![Captured mirrored mesh approval uses local coordinates while another mesh remains selected](../images/captured-mirrored-mesh-approval.png)

For a selected mirrored source, the dialog opened with local coordinates
selected. Escape cancelled; selecting scene coordinates showed rejection, and
returning to local coordinates allowed Return confirmation. Source scale
remained negative, Keep original retained a copy, and a second explicit reuse
persisted `mesh_edit` without more mock requests or submissions.

![Selected mirrored source with negative scale before saved mesh application](../images/mirrored-mesh-before.png)

![Mirrored source approval selects and explains local coordinates](../images/mirrored-mesh-approval.png)

![Applied mirrored mesh retains its negative source scale](../images/mirrored-mesh-result.png)

For an ordinary source, mouse input opened the explicit review and Escape
cancelled without applying. A fresh review named the selected source, and Return
confirmed geometry replacement with Keep original enabled: the source became the
synthetic three-vertex result, its original copy remained, and the durable job
became applied without another mock submission or request. Both policy and
coordinate menus, Keep original toggling and an explicit completed-result reuse
confirmed with Return also worked; reuse preserved the completed generation and
recorded one separate applied local claim. Viewport selection, focus and
front-view keyboard input worked after application. These checks do not
establish provider alignment.

[Before application](../images/saved-mesh-edit-before.png),
[approved replacement result](../images/saved-mesh-edit-result.png).

![Native mesh approval identifies the source and replacement policy](../images/saved-mesh-edit-approval.png)


## Captured mesh source interaction evidence

The saved-job **Apply to captured source (N)** action opens the existing mesh
review with the original exported object, independently of active selection.
Its extra line identifies the unchanged captured source. **Apply mesh edit (N)**
keeps explicit current-destination review; both require confirmation.

With a real source export and another mesh active, mouse activation named
`Cube.001` as the captured source. Escape canceled without changing the saved
ready record or either mesh; viewport focus and numpad front view still worked.
Reopening and confirming with Return replaced the source's eight vertices with
the saved three-vertex fixture, retained an original copy, and left the other
active mesh at eight vertices. The job became applied with no additional mock
submission, service request or download, and a socket guard recorded no network
attempts.

![Captured source confirmation names the exported cube while another mesh remains active](../images/captured-mesh-source-approval.png)

![Applied captured source retains its original copy and leaves the other active mesh unchanged](../images/captured-mesh-source-result.png)

This covers local source selection, cancellation and confirmation, not provider
alignment. See
[the source contract](../MESH_APPLICATION.md#applying-to-the-captured-mesh-source).


## Retexture review

The mesh review's **Replace textures** choice preserves geometry and adopts all
result UV layers and mesh material assignments. Its two explanation lines name
that replacement and require exactly matching indexed topology and positions.
Keep original and coordinate placement remain explicit, and drawing stays read-only.
Both current-destination and captured-source review use this policy.

Mouse selection exposed the policy and its geometry-preservation explanation.
Escape canceled without changing materials, geometry or local claims. A fresh
review selected the policy using the native menu and keyboard; Return applied
it with Keep original enabled. Vertex positions stayed identical, the saved
material replaced the fixture's blue material, and one separate local claim
became applied while the completed generation stayed applied, with unchanged
mock submissions and requests. Viewport click, front-view and orbit keys,
Outliner selection and zoom worked. These images do not show provider appearance
quality or indexing.

[Before retexture](../images/saved-retexture-before.png),
[applied retexture with original retained](../images/saved-retexture-result.png).

![Retexture review explicitly preserves geometry and requires matching topology](../images/saved-retexture-approval.png)


## Saved mesh undo interaction

The approval dialog explains that Keep original retains an unselected copy,
Blender settings control undo, and history changes leave jobs and spending
recorded. The shared command uses native history for every mesh policy;
see [the contract](../MESH_APPLICATION.md#native-undo-for-saved-mesh-edits).

Mouse input opened captured-source review while another mesh was selected, and
Return confirmed. The source changed from eight to three vertices with its
original copy retained; the other mesh stayed at eight vertices. Edit > Undo
restored the eight-vertex source and removed the copy. Edit > Redo restored the
three-vertex result and its copy. The saved job stayed applied and mock
submission and request counts stayed unchanged throughout. Public job status
remained readable: `mesh_edit` became null on Undo and remained null after Redo
instead of following recreated objects by name. Viewport zoom and front-view
keyboard input worked after Redo.

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

Native clicks and keyboard input selected the policy, cancelled without mutation,
then confirmed application to the captured source while another mesh remained
selected. The source became an empty mesh parent with two named triangle parts;
Keep original retained its eight-vertex copy and the other mesh kept eight
vertices. Edit > Undo restored the eight-vertex source and removed the parts and
copy. Edit > Redo restored both children and the copy. The public job stayed
applied, transient mesh status retired on undo, and mock submission/request
counts did not change. Viewport zoom/front-view input and Outliner expansion
remained usable.

[Applied parts and preserved selection](../images/saved-mesh-parts-applied.png).

![Parts approval names the target and explains grouping](../images/saved-mesh-parts-approval.png)

Confirming single-mesh replacement with a two-mesh fixture failed without
changing either source or selection. **Job needs review** opened the full message
identifying the saved GLB, source and edit policy. Escape closed it and
front-view keyboard input worked in the viewport, with no mock submission,
request, download or network attempt.

## Animated model import interaction

The screenshots show the earlier **Import model** label; current buttons are
named by format, as in [Saved model package review](#saved-model-package-review).
Its review names the scene
and cursor and explains a new group, packed textures, preserved selection,
retained rigs/clips and unchanged timeline. Drawing remains read-only. The
[import contract](../MESH_APPLICATION.md#rigged-and-animated-model-import) describes
clip timing, staging isolation and the separate in-place transfer boundary.

The review opened, cancelled without importing, then confirmed a new character
with two bones and two clips. The original cube remained active. Native viewport
zoom/front-view input and Outliner expansion worked. Clicking frame 30 on the
timeline animated the rig and skinned/morphed triangle from its frame-zero
state; evaluated vertices moved two units in X and one unit through the morph.
FPS stayed 30 and the range stayed 1 through 90. The saved job stayed applied and
mock submission/request counts stayed unchanged. This does not establish provider
rig compatibility or in-place retargeting.

[Frame zero](../images/saved-model-animation-start.png),
[frame thirty](../images/saved-model-animation-end.png).

![Model import approval explains retained rigs, clips and timeline behavior](../images/saved-model-animation-approval.png)

## Rig attachment interaction

The saved-mesh review offers **Attach rig**. It names the captured source and
explains matching geometry, retained source UVs/materials, bone weights and clips,
Keep original and native undo. It also explains that the source and new rig group
must move together afterward. For a source already skinned to an armature, the
review starts on Attach rig unless an edit was chosen or the job is an Animate
job, which starts on Apply animation; it says the old rig stays and that Keep
original's copy uses it, and names Attach rig or Apply animation when another
edit is selected. Drawing stays read-only; the shared UI/MCP command implements
the [skin attachment contract](../MESH_APPLICATION.md#attach-a-returned-rig).

Desktop input selected Attach rig, cancelled without mutation and confirmed
against the captured triangle while another mesh stayed selected. The source
retained its geometry, gained two bone groups and an armature modifier, and Keep
original retained an unselected copy. Native Edit > Undo removed the rig, groups
and copy; Redo restored them. The saved job stayed applied and its transient mesh
status retired on undo. Mock submission/request counts stayed unchanged. Viewport
zoom/front-view input and Outliner expansion worked; clicking frame 30 moved the
skinned source two units in X while the original stayed still. This does not
establish provider compatibility or existing-rig retargeting.

[Animated source, original copy and preserved selection](../images/saved-mesh-rig-animated.png).

![Rig approval names the captured source and explains compatibility](../images/saved-mesh-rig-approval.png)

## Animation application interaction

The saved-mesh review offers **Apply animation**. It names the captured source
and explains that the returned clips go onto this mesh's rig while its mesh and
skin stay, that bone names, parents and rest pose must match and clips are
scaled to the rig, that the first clip plays while it, the others and the
previous action stay in NLA, that the returned character is not added and the
timeline stays unchanged, and how Undo behaves. **Result coordinates** and
**Keep original** are not shown because ANIMATE changes no mesh data. A skinned
source starts on Apply animation for an Animate job or when it was requested,
otherwise on Attach rig; choosing Apply animation for an unskinned mesh shows
**Apply animation needs a mesh skinned to an armature**. Drawing stays
read-only; the shared UI/MCP command implements the
[animation contract](../MESH_APPLICATION.md#apply-returned-animation). When the
keys were corrected for a rest difference, the job row then shows **Clips
adjusted to this rig's rest pose by up to N°** until undo history changes.
