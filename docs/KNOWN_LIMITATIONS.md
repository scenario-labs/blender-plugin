# Known limitations

This page distinguishes inspected code limitations from unverified service or
platform behavior. See the [audit](maintenance/backlog.md) for the disposition
of older reports and the [runtime map](architecture/runtime.md) for integration
boundaries. No paid or live acceptance is implied by this documentation.

An offline Render Image desktop probe on macOS arm64 / Blender 5.0.1 reached
a ready quote, accepted text edits, submitted once through a synthetic transport
and retained viewport navigation. It later crashed with the native traceback in
a background SQLite job read. Subsequent diagnostic polling, screenshot and
144-second native interaction probes on that same ZIP completed cleanly, including
shutdown and normal-profile preservation.
[#263](https://github.com/scenario-labs/blender-plugin/issues/263) was closed on
2026-10-04; its public record does not document a root cause or verified fix.
The historical failure and clean reruns are evidence limits, not a claim that
the current candidate reproduces the crash. Current-candidate sustained desktop
acceptance remains under #68; synthetic probes and passing headless tests do not
establish live generation or full render-lane desktop acceptance.

## Runtime and authentication

- The Image lane now shares SDK quotes, durable submission, reference uploads
  and result/recovery commands between UI and local MCP. All MCP `generate`
  lanes now use shared quotes, durable submission and downloads; only Image
  automatically imports results. Native form generation now uses those shared
  quotes and jobs too. Files, mesh/clip captures and render scene/first-frame inputs
  use explicit uploads before the final quote. The native **Use as video first
  frame** control and local MCP can instead hand a downloaded saved PNG, JPEG or
  WebP result to the Render Video first frame by reusing its asset ID. A free
  dry run resolves that asset ID (an unknown ID returns HTTP 404) but does not
  check which inputs may be combined: on 2026-10-10 it priced a Seedance 2.0 Fast
  first frame sent with the scene clip. The service accepts that submission, then
  the job fails because an image and reference videos aren't allowed together.
  Seedance 2.x, Minimax H3 and Wan 3.0 state that limit only in input description
  text. Their first frame is now sent as image 1 of the reference images with the
  clip, and every shared quote path refuses a first frame sent with reference
  images or videos on these models (see the input-exclusivity limits below). No
  successful paid Render Video job has used a first frame sent this way, so how
  closely the clip opens on that image is unverified. The native control has
  installed tests only: its desktop interaction and the undo step recorded from
  the maintenance pump are unproven on Blender 5.0, 5.1 and 5.2. The handoff
  stores no file path, so the blend shows no first-frame thumbnail. Render forms
  accept a written look or the default look with automatic Spark disabled. An
  empty automatic look requires its own exact Spark quote, approval and guarded
  result delivery before
  the final render quote. Film task quotes, approvals and saved-upload associations
  now share these jobs through native controls and MCP. Film shot construction
  uses separate saved-model verification and build approval. Synthetic desktop
  shot interaction, including Undo/Redo, passes on macOS Blender 5.1.2; live
  provider, other OS/DPI and motion/audio acceptance remain separate. Local
  timeline assembly requires explicit selection of completed shot scenes and
  confirmation; it creates editable scene strips without generation or rendering.
  Synthetic timeline selection, cancellation, Undo/Redo and Sequencer inspection
  pass on macOS Blender 5.1.2; see [the evidence and limits](UI_STYLE.md#film-timeline-controls).
  Local capture now shares explicit native/MCP approval, cancellation and separate
  byte-checked upload. Capture reviews/files are session-local. Desktop still
  capture, cancellation of approval dialogs, synthetic upload and cleanup pass on
  macOS Blender 5.1.2; see [the evidence and limits](UI_STYLE.md#film-capture-controls).
  Desktop video cancellation, live uploads, other OS/DPI and sustained media
  acceptance remain pending. Composition preparation, exact pricing and separate
  generation approval now share native/MCP controls and preserve saved masters
  after restart. Synthetic composition approval, mode navigation, invalidation and
  saved-job inspection pass on macOS Blender 5.1.2; see
  [the evidence and limits](UI_STYLE.md#film-composition-controls). Live provider
  acceptance and other OS/DPI behavior remain pending. Native/MCP review assembly
  now prepares private saved-media copies and separately approves a new review
  scene with application claims; it has installed synthetic coverage only, and
  desktop interaction, live media and human motion/audio review remain pending.
  A frame, recipe or object edit, object selection, an Undo or Redo, building
  another review for the same scene, or leaving the recipe scene and selecting it
  again, before building deletes the copies and requires a fresh preparation;
  Undo after a build keeps them. See
  [review controls](FILM_PLAN.md#native-and-mcp-review-controls). Native/MCP
  [video export controls](FILM_PLAN.md#native-and-mcp-video-export-controls) render
  a built review scene to a new MP4 after a destination choice and a separate
  render approval; agents may write only inside the Output Folder. They have
  installed synthetic coverage only; desktop interaction and human playback review
  remain pending. A ready export is invalidated by the same scene changes as a
  review, and one export runs at a time. An edit made to the review scene without
  showing it, for example from a script, is noticed only at approval and only when
  it changes the frames, rate, size, strip or media counts or audible sound shown.
  A [portable case-study bundle](FILM_PLAN.md#portable-case-study-bundle) packs a
  built review, an optional timeline with its shots, their media, the sanitized
  recipe and a production ledger into a new ZIP; it shares that thread, refuses
  linked data (including the Essentials brushes a scene links once a sculpt or
  paint mode was used in it), movie clips, packed sound strip audio, image
  sequences and other unportable data, keeps model IDs in the recipe and cannot
  clear Blender's unused bytes of earlier settings, so review a bundle before
  publishing it widely. It notices an edit of its unshown scenes only through the
  review's frames, rate, size and strip count, the scene and media counts and bytes
  and the ledger. It has installed synthetic coverage only. Video export
  verification uses an installed ffprobe when present and otherwise a weaker
  Blender decode check. Blender builds without H.264/AAC encoders cannot export;
  they are detected only when the render child fails, with its log retained.
  Complete runtime adoption and live/native acceptance remain open
  ([#64](https://github.com/scenario-labs/blender-plugin/issues/64),
  [#65](https://github.com/scenario-labs/blender-plugin/issues/65)).
- Credentials use one explicitly selected pair (saved Blender preferences by
  default, environment only when selected). UI and MCP model jobs use credential-bound
  local storage. Preferences also allow an explicit optional project ID; changing
  it retires approvals and selects separate saved jobs. Blank uses the API key's
  default scope without discovering its identity. Live project permission and
  cross-project service acceptance remain under #68; browser sign-in in
  [#67](https://github.com/scenario-labs/blender-plugin/issues/67) is deferred.
- An uncertain submission is currently not reconciled automatically. Its saved
  job stays marked as unconfirmed and offers no resubmission. If a model job
  completed, recover it from cloud history with **Save for recovery** (local MCP:
  `recover_cloud_job`) instead of generating again. Uncertain workflow and
  prompt-helper submissions currently have no in-Blender recovery. Do not repeat
  them; check their outcome in the Scenario web app.
- Remote cancellation is offered only for jobs Scenario reports as `inference`,
  the only type its job action reference documents as cancellable. Captured
  model generations report `custom`, so Blender does not cancel them; they
  finish or fail on Scenario and stay recoverable. Which lanes return
  `inference` and live cancellation acceptance remain open under
  [#65](https://github.com/scenario-labs/blender-plugin/issues/65).
- Trained/custom-model discovery and routing remain incomplete
  ([#97](https://github.com/scenario-labs/blender-plugin/issues/97)).
- Remote job progress is advisory and kept only in memory. Providers may report
  no fraction, or 0 until completion, so a job may show only `generating`; no
  time estimate is given. Readings and the submitting scene/lane binding are not
  persisted: after a restart, progress appears only after an explicit refresh or
  resume, and recovered jobs remain unbound. Which providers report intermediate
  fractions, and desktop review of the progress bar, still need live and
  [#66](https://github.com/scenario-labs/blender-plugin/issues/66)/[#68](https://github.com/scenario-labs/blender-plugin/issues/68)
  evidence. See [the projection rules](BLENDER_JOB_CONTEXT.md#remote-progress-and-scene-lane-binding).
- Scenario cannot cancel a running workflow step: rejecting a waiting approval
  or selection step (**Stop workflow**, or MCP `decide_workflow_step` `reject`)
  is the only way to stop a workflow, and completed steps stay charged. Steps
  inside a nested workflow node are not shown. A selection that feeds a ForEach
  loop, a nested workflow or a node type the API reference does not list can
  only be rejected until live evidence shows its charge stays within the
  approved price. So can any selection in a workflow with such a node when the
  links between its steps cannot be read from the job or the workflow
  definition; an approval then warns that its review assets may be incomplete.
  Review assets and candidates are asset IDs or text until
  **Load previews** fetches private previews: a PNG, JPEG or WebP asset larger
  than 8 MiB or 4096 pixels per side, or another kind of asset, is previewed
  only through a server thumbnail Scenario offers, and MCP returns no preview.
  The native dialog shows at most 12 wrapped lines of each text candidate.
  Decisions are not live-verified, including repeated or concurrent decisions,
  omitted project IDs and rejection inside a loop, and neither are the review
  assets and preview sources real flows list; desktop interaction evidence for
  the native review and its previews is pending
  ([#65](https://github.com/scenario-labs/blender-plugin/issues/65),
  [#66](https://github.com/scenario-labs/blender-plugin/issues/66)). See
  [waiting workflow steps](UI_STYLE.md#waiting-workflow-steps).

## Creation and scene application

- MCP Render Image/Video now share native form preparation, uploaded references,
  prompt decoration and exact approvals. Live provider and desktop acceptance
  remain open under #65/#68; scene captures require a GUI.
- Input combinations are checked only where model descriptions state them. No
  schema field marks inputs that cannot be sent together, and a free dry run
  prices such a body. In every lane, the shared quote path refuses two file
  inputs when one's description says it can't be combined with the other. On
  2026-10-10 that matched 11 of 709 public models: first or last frames with
  reference inputs on Seedance 2.5, 2.0 Fast and 2.0 Mini, Minimax H3 and Wan
  3.0 (Video and Render Video lanes) and on the deprecated Seedance 2.0;
  reference images with an input video on Gemini 3.1 Flash and Nano Banana 2.1
  (Image lane); an image with a video on Wan 2.7 i2v, which no lane lists; and
  audio references with an image reference on BytePlus Seed Audio 1.0 and its
  multilingual version (Audio lane). Differently worded limits are not caught.
  Settings and item counts stated only in text are not checked either, so those
  limits are left to the service, for example: Kling V3 Omni's Generate Audio,
  or its 4K mode, with a reference video, and more than 4 reference images with
  a video; Luma Ray 3.2 Edit's guide frame with keyframes; Meshy's Texture
  Prompt with texture reference images; Tripo v3.0 Texturing's text prompt with
  its image prompt; Recraft V4 Styles' style ID with style reference images; and
  Meshy Smart Topology's prompt with its image. Over the curated models, the
  weekly payload audit fails only on a file input whose wording names no sibling
  input. Recognized exclusivity wording ("mutually exclusive with", "can't be
  combined with") that involves a setting is listed at `MED`; other wording,
  such as Kling V3 Omni's 4K mode and reference-image count, is not reported.
- Reversible mesh and panoramic World application exist as explicit synchronous
  primitives. Full generation/history integration remains
  [#99](https://github.com/scenario-labs/blender-plugin/issues/99) and
  [#98](https://github.com/scenario-labs/blender-plugin/issues/98).
- The Environment lane (sidebar, Studio, the composer's Generate mode and local
  MCP) generates 360 panoramas, HDRIs and upscales only through verified model
  contracts, and its results wait for explicit World approval. Output formats and
  sizes, the HDRI asset layout, seam and pole quality and the measured HDR range
  still need an authorized live run. A physical desktop pass covered the form,
  free quotes and World application before the lane was rebased onto #394; the
  rebased composer tab row, a local panorama file upload and From image beyond
  its quote still need desktop evidence under #98. A panorama input takes a
  saved 360 result or a checked local 2:1 file; local MCP accepts only the saved
  result.
- Multi-object mesh export combines the selection. Safe in-place multi-object
  editing needs separate acceptance under #99.
- Automatic Image-lane import and saved image and material application
  currently accept only PNG and scanline OpenEXR files. World application also
  accepts baseline or progressive JPEG and ACES-labelled OpenEXR panoramas.
  Other image results, such as WebP, or JPEG and ACES-labelled OpenEXR outside
  World, stay saved with the job without import.
- Saved GLB, JSON glTF, FBX, OBJ and mesh PLY results import as a new group, but
  package binding without persisted asset lineage is conservative: several OBJ or
  glTF files, several MTLs or several maps for one slot stay unbound and are
  reported, so such a job imports untextured or not at all. An FBX that references
  external texture files is rejected (Blender's importer may read that file before
  the rollback), and an animated FBX keeps the file's frame rate when the scene
  uses another. ASCII FBX, ksplat, sog, STL and USD results are not imported.
  Snapshot copying and hashing are synchronous on the main thread. Provider
  package shapes, including whether glTF JSON is delivered at all, need live
  evidence (#65).
- Saved Gaussian splats (SPZ v2/v3, 3DGS PLY and .splat) import as a coloured
  point cloud, not as rendered Gaussian splats: rotations, anisotropic scales,
  view-dependent colour and sorted alpha blending are not reproduced, and files
  denser than the reviewed point limit (at most 2,000,000) are thinned evenly.
  SPZ v4 (ZSTD), the pre-release v1 and compressed splat PLY files cannot be
  decoded; their files are kept. SPZ extension records, including a declared
  coordinate system, are not read; the job row and MCP only flag their presence.
  The default saved axes follow each file format's convention and still need live
  visual evidence for provider worlds; choose the other axes in the review when a
  result is not upright. Viewport performance at 1,000,000 or more points is not
  established (#65).
- Prompt helpers require their own exact quote and approval. Unusable Spark
  output fails without an automatic paid LLM fallback; complete text can be
  retrieved again without regeneration. Historical prices are not current quotes.
- Studio workflow file inputs upload image, audio, video and 3D files or
  snapshots only. Inputs declared as other kinds (for example `image-hdr`,
  `document`, `json` or `text`) or with listed allowed asset IDs still need a
  Library selection or a typed asset ID. An upload that is still sending stops
  for good after a scene edit, frame change or undo; it does not resume, so the
  content is uploaded again (see the [user guide](USER_GUIDE.md#run-a-workflow)).
  Workflow and generation-form uploads share 128 upload handles; finished
  uploads keep theirs until the credentials or project change, a blend file
  loads (Open, Revert or File > New) or the extension restarts. Live workflow
  upload and native interaction acceptance remain under #66/#68.
- Video-to-motion and speech-to-text workflows remain an explicit capability
  request in [#190](https://github.com/scenario-labs/blender-plugin/issues/190);
  model tags alone do not establish supported input and result handling. Models
  offering `video23d` or `audio2txt` show a visible experimental status in the
  picker, the Model row and `list_models`; the viewport composer's model chip
  does not show it. They can be submitted; provider behavior and result handling
  are not accepted. Generic import by file type may still bring in a returned
  model (GLB, glTF, FBX, OBJ or mesh PLY) or media file.

## Interface and capture

- The prototype composer and sidebar expose different controls. Model schema
  loading, long-prompt editing and compact/expanded behavior need the native
  acceptance in [#66](https://github.com/scenario-labs/blender-plugin/issues/66).
- Input methods (IME) cannot compose in the composer prompt. Blender composes
  only in its own text fields and gives add-ons neither the composition text nor
  a Python type for its composition events, so the composer receives raw keys
  (romaji, for example). F2 in the focused prompt opens a native text field
  whose text is added at the caret; a composition starting in the focused prompt
  (two untyped presses without text in a row) opens the same field, so it no
  longer stays pending for the next native field. A lone such press, as a dead
  key sends, opens nothing. The field does not open while another form has
  replaced the focused prompt's or when the form's model takes no prompt, the
  cases where typed keys are refused too, so a composition started then can
  still stay pending. In an input mode that commits each key, the first
  key's text arrives in the second press the composer consumes and is lost.
  Inspected Blender 5.0.1, 5.1.2 and 5.2.1 macOS source ends input-method state
  only after a text edit that received a composition. After another edit, such
  as an Outliner rename cancelled with Esc, selecting an input method can route
  keys to it while no field is editing; by that reading, letter keys then miss
  viewport shortcuts too. Installed tests simulate these events; physical
  composition, candidate-window placement and other platforms' input methods
  remain unverified under #66.
- The composer's [job strip](UI_STYLE.md#compact-job-strip) shows only jobs
  submitted from that scene and form in the current Blender session: jobs from
  before a restart, recovered cloud jobs, workflows and Film tasks are not bound
  to a form and stay in Jobs. A viewport too small for the tray hides it. While
  an automatic status refresh runs, its held action answers *try again in a
  moment* instead of dispatching. The confirmation, destination dialogs and job
  card a strip click opens from the composer have only headless coverage so far;
  desktop interaction, alternate UI scales and screenshots remain #66 work.
- Viewport screenshots and OpenGL capture require a GUI. Automated GUI probes
  can take keyboard focus; follow the isolated-profile validation procedure.
- Saved shared video and audio results offer **Play**, **Play in Blender** for
  video and **Waveform** for audio in their saved-job controls. Retained
  prototype results keep Play and Add to sequencer, without a waveform. Beyond
  installed-ZIP native tests, partial physical desktop passes on macOS arm64
  Blender 5.1.2 opened a saved video in the system player and in Blender's
  animation player at UI scale 1.0, and drew a waveform in the sidebar at UI
  scales 1.0 and 2.0. The last pass's ZIP wrapped the waveform status by
  measured width, before later amendments for Studio's popup width and
  hyphenated words, and kept the duration with its unit. Play audio, the
  waveform's Cancel, Retry and close on the desktop, clicking Play at UI scale
  2.0, Studio at UI scale 2.0, other platforms and human listening have no
  desktop evidence yet, which remains
  [#189](https://github.com/scenario-labs/blender-plugin/issues/189), #66 and
  [#68](https://github.com/scenario-labs/blender-plugin/issues/68) work. Local MCP
  cannot read waveform envelopes yet, and no MCP tool launches a player. See the
  [supported limits](USER_GUIDE.md#audio).
- Play first copies the saved file, up to 512 MiB, on the preview lane, so a
  large file waits for its copy and queues behind server thumbnail polls and
  waveform decodes there. Up to four copies or 1 GiB are kept for reuse, plus any
  copy a running animation player reads. The system player is not tracked: an
  eviction, connection change, file load or disabling the extension can remove a
  copy it still has open, and on Windows and Linux it can inherit Blender's
  environment, including credentials from Credentials > Environment. Windows
  refuses to delete a copy a player still holds open; it is removed by a later
  day's sweep. Whether Blender's animation player plays a video's soundtrack,
  behavior without a default player (for example Linux without `xdg-open`) and
  sandboxed Blender packages are unverified. Without a usable executable path,
  Play in Blender fails with an explicit error.
- Each waveform starts a separate offline Blender process: a one-second file took
  0.65 to 0.9 seconds end to end on macOS arm64 with Blender 5.0.1 to 5.2.1.
  Windows and Linux start-up, antivirus interference and sandboxed Blender
  packages are unmeasured. Without a usable executable path, waveforms fail with
  an explicit error.
- A waveform decode occupies the single preview lane for its duration, at most
  60 seconds; Cancel terminates its decoder process. A decode that cannot start
  within 120 seconds, for example behind other lane work, fails with Retry. The
  shown waveform is drawn from its cached envelope and checked once per second
  for a changed connection; it does not monitor later external file changes, but
  every Play and decode rechecks the saved receipt.
- Prompt helpers lack an explicit generic/model-contextual Spark preference
  ([#188](https://github.com/scenario-labs/blender-plugin/issues/188)).
- Capture timing follows scene settings; native dialogs use Blender's theme
  rather than the custom composer drawing.
- Studio > Library [organization](UI_STYLE.md#library-organization) changes one
  asset per review (local MCP accepts up to 49) and loads at most 200 collections.
  Applied changes are immediate account metadata that Blender Undo does not
  reverse. Collection rename and deletion, model collections and tag listing are
  not available, and pages loaded with Public assets cannot be organized. Reviews
  and results are session-local: a restart, file load or connection change loses
  the card, while a sent write keeps its effect. Search results may lag behind
  tag changes; verification reads the assets back instead. An add of an asset
  that is already a member is refused as a whole and writes nothing, as the
  service was observed to behave; the review then reads the asset back as
  verified without another request. This is not yet checked live from this
  repository. DELETE body survival through the production edge, name uniqueness,
  tag normalization and service limits are unverified live. On macOS, Japanese
  IME composition did not start in the Organize dialog's Tags field, as in
  Blender's own text fields, where pasting the text worked. Apply on a desktop,
  and the card placement and read-enabled controls described in the UI contract,
  still need a physical desktop check under
  [#66](https://github.com/scenario-labs/blender-plugin/issues/66).

## Verification

Offline contracts establish the behavior of fixtures and local state machines.
Live OAuth acceptance, provider behavior, full UI/MCP parity and supported
platform interaction remain separate gates in
[#68](https://github.com/scenario-labs/blender-plugin/issues/68).
Inherited historical reports must be reproduced before being called current
bugs. Passing a knowledge check establishes structure and freshness signals,
not prose truth or runtime correctness.
