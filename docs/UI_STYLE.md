# Scenario for Blender: UI style guide

The N-panel is drawn with Blender's `UILayout`, so it wears the user's Blender theme (colours, corner radius, fonts). We cannot change those; what we control is structure, spacing, wording and icons. This guide keeps the whole plugin coherent. The floating composer is custom gpu/blf drawing and mirrors the same language.

## Tabs and segmented choices

A row of mutually exclusive choices (lane tabs, picker modality tabs and category chips, Edit 3D tasks) is a **continuous segmented control**: cells touch (no gaps), each takes an equal share of the full width, and the icon sits next to its label with the pair centred in the cell.

- Use `panels.equal_segments(row, struct, prop, values)` (or `panels.draw_enum_tabs(layout, struct, prop, rows)` for multiple rows). It draws each value with `prop_enum` inside an `align=True` row (Blender merges the borders) and forces equal widths with a chain of even `split()`s.
- Never use `prop(..., expand=True)` for these (it pins the icon to the left edge) or `grid_flow` (it leaves gaps).

## Sections

Each group of controls is a `layout.box()` with a one-line header: `box.label(text="Title", icon=...)`. Order inside a lane: Model, Prompt, References, Settings, then the Generate button. Put `layout.separator(factor=0.5)` between the tabs and the form, and above the Generate button.

Every section header carries an icon so the panel reads as a stack of peers: `Model` (`NODE_MATERIAL`), `Clip to render` (`RENDER_ANIMATION`), `Camera path` (`CAMERA_DATA`), `Rendering Style` (`BRUSH_DATA`), `Settings` (`PREFERENCES`). Sections do not collapse (no chevron): a header is a static label, not a toggle, so the form is always visible.

## Buttons

- The **Generate** button is the one primary action: `row.scale_y = 1.5`, icon `PLAY`, and it always shows the live price (`Generate (15 CU)` / `Generate (from N CU)` / `Generate (estimating...)`).
- Icon-only buttons keep Blender's fixed size; a button that must fill a row carries a short label (Blender never stretches an icon-only button). The three prompt tools are `New`, `Rewrite`, `Translate`.
- Destructive actions (`Delete`, `Clear path`) ask for confirmation (`invoke_confirm`).

When Blender online access is disabled, the composer shows **Offline** on its
disabled generation button and **Online access disabled** instead of a loading
message when no model is available. Pending edits retain their estimate request
until online access and credentials are available. The generation controls
remain disabled until a ready quote handle exists; the submission path still
rechecks its exact inputs, origin and approval. A model list is only described as
loading while a catalog request is active.

## The model chooser

A `Model` section (a box with a `NODE_MATERIAL` header, like the others) holds a wide button (icon + model name) that opens the picker, with the native dropdown as a small fallback on the right. Its one-line description belongs in the picker, not the panel.

## Duration and Match timeline

The video model's `Duration (cost)` drives the camera-path duration for **Render
Video** when **Match timeline** is on. The planner tells users to build the path
before capture. Capture uses the displayed preview/scene range without implicit
padding or trimming. Uploaded clips remain unchanged when timeline/model settings
change. The base **Video** lane keeps the reverse setting direction: the model's
duration follows the scene frame range through `generation.apply_match_timeline`.

## Reference inputs

A file input's add options match its kind (`props.addable_sources_for`): a **3D** input offers a model file and **Upload selected mesh** when a mesh is selected; an **image** input offers Upload plus the viewport/camera stills and the render result; a **video** input offers Upload plus the clip captures. Never offer a source that produces the wrong asset type (no image capture on a 3D character input).

A selected mesh appears as a candidate for each empty **3D** input. **Upload
selected mesh** explicitly exports the selection as one GLB and uploads that
snapshot. A pending or completed explicit reference replaces the pinned candidate;
do not offer a second mesh upload into an occupied slot. Edit 3D still requires
an input mesh. Later scene edits do not change an already uploaded snapshot.

Across generation forms, attaching a local file does not send it. Image inputs
also support explicit viewport, camera and Render Result snapshots. Video inputs
support viewport/camera clips over the preview range, or scene range when no
preview is enabled, without implicit padding or audio. Grey clay capture is
applied when selected. Do not offer an image Render Result for a video input.
The separate **Upload reference** button sends an immutable snapshot before a
final price can be requested. Show upload progress and **Inspect uploads** when
review is needed. Do not offer automatic retry for uncertain uploads or mutate
the reference during drawing. The maintenance pump attaches a completed asset
only to the unchanged original scene, lane, model, input type and reference slot,
then invalidates the old price. A removed/edited slot must never receive a late upload result.
Transient timer context without the originating scene pauses attachment. Local
validation rejected before task admission permits correcting and retrying the input;
uncertain admitted work retains its duplicate-upload guard.

**Inspect uploads** offers explicit known-status refresh, unclaimed preparation
cancellation and finished staging cleanup; cancellation/cleanup require confirmation.
**Use saved upload** and an input's **Saved uploads** open the same paginated
view. Offer attachment only for imported uploads matching the input kind
(image, audio, video or 3D). Attaching one needs a separate confirmation of its
scene, lane, model, input and reference destination. A changed destination must
be reviewed again. Pending or uncertain marked uploads block generation so the
prototype path cannot upload the same file a second time. Recheck that destination
on confirmation, keep drawing read-only and invalidate the prior generation price after attachment.

Render forms show **Capture and upload scene** in their scene/clip section, with
that slot's progress, inspection and removal controls. Render Video's optional
first frame always exposes a file field and native folder picker, followed by a
separate **Upload first frame** action after choosing an image. Do not draw these slots
again as style references. The scene snapshot precedes styles; a first frame
precedes other images in the same array. Disabled first frames are omitted without
canceling or deleting their upload. Changed first-frame paths require explicit
replacement. Result reuse must not silently replace a role-tagged single-file
scene or first-frame slot; require explicit removal first. Changing the path or automatic Spark option invalidates the price.
An empty look with automatic Spark enabled blocks quoting; display its unavailable
status until separate Spark approval is integrated. Drawing remains read-only.

## Generations

**Remove background** prepares the Image form and never submits directly. Its
message tells users to upload the reference, review the price and choose
**Generate**. Validate the file and available model/schema before replacing the
form; reset the old prompt/settings/references and invalidate the previous quote.
Existing jobs and admitted uploads keep their own lifetime and origin guards.

Each result collapses on its own; the panel header has a **Collapse all / Expand all** toggle. A failed result shows a red error control in its header whose tooltip is the whole message (with the Error ID) and which opens the full text with a Copy button on click (a `description()`-driven operator, since Blender labels have no per-instance tooltip). Never truncate an error to a single clipped line as the only way to read it. The prompt box carries a trash button that deletes its text, greyed out when empty.

## Wording

- Verbs on buttons say exactly what happens: `Generate`, `Add to scene`, `Use as reference`, `Refresh cloud`, `Download and open`.
- Singular/plural is correct: `1 Job` / `3 Jobs`, `Applies to 1 selected mesh`.
- Prompt helpers request a free exact server price first. Show the formatted CU amount below the tools with a separate action-labelled approval button. Do not use a fixed price or a tooltip as spending authorization. Keep pending/error text readable; an uncertain job offers inspection, never automatic resubmission.
- CU labels follow the web generation indicator: up to three decimal places,
  no trailing zeros, and thousands separators below 10,000; at or above 10,000,
  use K/M/B/T with three significant digits (`0.123 CU`, `1,234.568 CU`,
  `12.3K CU`). This is display formatting only. Keep the original server decimal
  in the quote, approval action and saved job; never reconstruct it from the label.
- No internal names in user text (a person sees `Reference Images`, not `referenceImages`).

## Tooltips

Every operator sets `bl_description`: one sentence, action first, the cost when it spends credits. Blender adds the trailing period.

## Icons

Modality icons (image, video, audio, 3d) are Scenario's own PNGs (`scenario/icons/`, loaded by `blender/icons.py`, `icons.kwargs(name)` with a built-in fallback for headless). Section and action icons are Blender built-ins chosen to read at a glance.

## Status messages

`runtime.set_message(...)` lines are transient: `runtime.message_visible()` hides them after 8 s so a stale line never reads as current.

## What Blender cannot do (so we do not fake it)

- Text is left, centre or right aligned, never justified.
- A panel text field is single line; a taller prompt box grows the field, it does not wrap for editing.
- Dialogs and the sidebar cannot take the composer's custom colours; their layout follows this guide, their palette is the Blender theme's.

## Prompt approval interaction evidence

These earlier offline Blender 5.1.2 macOS arm64 captures show the price before
approval and the delivered text afterward. The model, price and transport are
synthetic; they are not current service pricing or live generation evidence.
They predate the shorter CU labels described above. The price request made no
submission; the separate approval produced exactly one.
Native field editing, focus transfer and viewport selection/zoom were exercised.
Computer-control focus guards interrupted some typing attempts; this does not
establish exhaustive keyboard or clipboard acceptance. The isolated run exited
cleanly and left the normal profile unchanged. A disposable Blender copy used a
distinct application identifier and local development signature to distinguish
its window; the extension ZIP was unchanged. Supported-version packaged tests
remain separate from this single-version desktop check and unresolved #263.

![Full exact prompt price with a separate approval button](images/prompt-price-approval.png)

![Generated text delivered to the original prompt field](images/prompt-result-delivery.png)

Render forms label the empty-look option **Prepare look with Prompt Spark**.
Its price and approval remain inside the Look section, separate from Generate.
The following offline Blender 5.1.2 macOS arm64 fixture shows that boundary before
and after one synthetic approval. Native focus, a keyboard edit and viewport
selection/zoom were checked; the run exited cleanly with the normal profile
unchanged. As above, the test-only Blender app identifier/signature differed,
while the candidate extension ZIP was unchanged. This is not live render evidence.

![Separate exact Spark price before preparing the render look](images/render-spark-price.png)

![Prepared look in the original render form before generation](images/render-spark-result.png)

## Saved video and audio confirmation

Shared saved jobs show a separate **Add video/audio strip (N)** action for each
supported result. Its confirmation states the destination scene, exact frame,
one-strip operation, unused channel, unchanged timing and local-file dependency;
video additionally states that embedded audio is omitted. Cancel discards the
approval. Drawing reads the prepared fields without accessing files or changing
jobs. A changed scene, frame, record or credential context requires new review.

![Native saved audio confirmation names the scene and frame before adding one strip](images/saved-media-approval.png)

Offline desktop acceptance used the exact packaged ZIP
`3d831dc70efe10e0e5c2cf377e2044015e49f32814ed2da6b8649822ff76a2d2`
in an isolated Blender 5.1.2 profile on macOS arm64. The fixture began with one
mock generation and a saved WAV; mouse approval inserted one sound strip at
frame 27 without another mock submission or request. Viewport selection/zoom,
editor switching, scene selection and the Home key in the Sequencer worked.
Blender exited cleanly and the normal profile fingerprint was unchanged. The
test-only app copy used a distinct bundle identifier and local ad-hoc signature
for reliable window targeting; the vendor executable code and extension ZIP
were unchanged. This is desktop interaction evidence, not human listening,
paid provider acceptance, other OS desktop coverage or resolution of #263.
Native exact-ZIP tests separately decode synthetic MP4, WebM, MP3, WAV and OGG.

## Saved static model confirmation

Show **Import static model (N)** for each supported GLB result. The confirmation
names the selected scene and cursor coordinates, states that it adds one model
group with packed textures, preserves existing objects/selection, and excludes
rigged, animated and external-file GLBs. A changed cursor or scene requires fresh
approval. Drawing only reads prepared values.

![Native static model confirmation shows the selected scene cursor and supported import limits](images/saved-model-approval.png)

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

## Saved panorama approval and restoration

**Set panorama as World (N)** prepares one PNG/EXR result and identifies the
selected scene and current World. Explain the 2:1/equirectangular requirement,
packed image, preserved original World, LDR/HDR distinction and session-local
restore limit. The action's presence is a media-type offer; byte compatibility is
checked during application, never in drawing. Cancel discards the prepared handle.

After completed application, **Restore previous World** uses a separate prepared
approval. It names the current scene/World and explains that edited owned data
prevents restoration. Do not silently clear edits, reapply the job or reset its
completed state after restoration. Reference [the user guide](USER_GUIDE.md#apply-a-saved-panorama-to-world)
for screenshots and [the World guide](WORLD_APPLICATION.md#saved-result-ui-and-mcp-approval)
for the already-applied Image and file-load boundaries.

Offline desktop acceptance on macOS arm64 Blender 5.1.2 used exact ZIP
`c570617fdcc2e4ff5e5b424e08768843186a38a95eb6e58252cec6c471b262f1`.
Mouse approval applied a synthetic saved 2:1 PNG as one packed World; a separate
confirmation restored the original World and removed the restore action while
the job stayed applied. Mock submissions and request counts remained unchanged.
Viewport selection, front-view keyboard input and zoom worked afterward. Blender
exited cleanly and the normal-profile fingerprint was unchanged. The test-only
app copy used a distinct bundle identifier and local ad-hoc signature for window
targeting; vendor executable code and the extension ZIP were unchanged. This does
not establish actual HDR/seam quality, other OS desktop support, resolution of
#263 or release acceptance.
