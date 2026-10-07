# Film recipe contracts

The adopted [Film recipe helpers](../scenario/core/scene/film_plan.py) and
[scene-plan helpers](../scenario/core/scene/film_scene_plan.py) preserve bounded
planning, editorial timing, continuity declarations and reference ordering from
the selected Studio source. They are pure Python: they do not open files, contact
Scenario, submit jobs or mutate Blender.

This is the input contract for the remaining Film integration under #64/#65.
Native Film task controls and MCP commands now use these contracts. This does not
establish a Film generation journey or satisfy the [release gate](maintenance/release-plan.md).

## Recipe and timing validation

`validate_film_plan` returns a new normalized recipe. It rejects non-finite or
non-JSON values, cycles, recipes exceeding two million UTF-8 JSON bytes, unknown
structural keys, invalid transforms and ambiguous timing. It supports one to
fifty shots, at most three hundred upload/model tasks, and at most fifteen minutes
of editorial duration. Tasks have explicit names; another take needs another
task name. Model parameter objects are data and still require the selected
SDK model schema before a quote.

Text-field limits apply both before and after punctuation normalization. Replacing
an em dash with a comma and space cannot produce a value above its field limit.
Placeholder names are trimmed; names that then collide are rejected so no legend
entry is silently overwritten. Distinct names retain their order and meanings.
Scene object names must also be unique after normalization so motion targets are
unambiguous. Non-string names/kinds and excessively nested input report
`ValueError`, including recursion during copying or task-reference resolution.

Shot and task IDs allow up to 96 characters. Omitted `style_task`, `previs_task`
and `video_task` use the shot ID with `-style`, `-previs` or `-video` appended.
If that derived name exceeds 96 characters, validation names the field that needs
an explicit task ID. A 96-character shot ID remains valid with explicit task
names; validation does not shorten or rewrite task identities.

The adopted scene schema validates primitives, bounded locations/scales/colors,
camera paths and optional World settings. Its deterministic local templates are
identified as local templates; they do not call a generator. This schema retains
full transforms and camera/World data for Film. It does not replace the existing
[Blockout element schema](../scenario/core/scene/blockout.py) or its active
saved-result approval path.

Editorial durations and trims must land on frame boundaries. Adjacent shots
cover consecutive frame ranges without gaps. Source duration must cover the
editorial trim/window; the adopted source-duration contract still permits only
whole seconds from four to thirty. This inherited restriction is not a claim
about every provider's current model capabilities.
An editorial window longer than thirty seconds reports the `source_trim` plus
`duration` conflict, whether `source_duration` is explicit or omitted.

Audio helpers validate dialogue, sound effects and music tracks, source trims,
gains, looping and non-overlapping duck intervals. They calculate segments; they
do not decode, play or import audio. An omitted `audio_tracks` retains the
source's default looping score description; an explicit empty list disables it.
Neither case authorizes producing a score. `continuity_audit` compares declared
adjacent object states and intentional changes. Its `visual_verification` result
is always false: a matching declaration does not prove visual continuity.

## Credentials and task references

`project_id` is optional. An absent/null value means use the selected credential
scope, including the server's API-key default project. The helpers never discover
an account/team or infer a project. `require_plan_scope` rejects an explicit
recipe project that differs from the selected project override; callers must
check it before preparing service work.

`resolve_references` resolves `$task` or `$task:index` from ordered `TaskAssets`
observations in the exact selected [JobScope](JOB_STORAGE.md#identity-and-ownership).
Service, credential identity, project override and team must all match, including
when project/team are absent. A recipe's project field alone cannot authorize an
output. Missing tasks, invalid/negative/ambiguous indexes and foreign-scope
observations fail. Asset identifiers are opaque and need no `asset_` prefix.

The shared Film model-task command now constructs these observations from
matching completed scoped model jobs and explicitly associated imported uploads,
as described below. The pure helper itself does not read storage
or certify completion of a caller-supplied observation. Resolved parameters still
need a fresh exact quote, explicit approval and a durable task/submission binding;
resolution is not spending authorization. No separate Film runner, client or
production-state database is introduced here.

## Durable model tasks

`JobCoordinator.quote_film_task` validates a raw recipe in the selected scope,
resolves completed model-task references and uses the existing SDK model schema
and exact estimate command. `JobWorkers` and `JobSession` expose it on the same
bounded queue and main-thread origin delivery as ordinary model quotes. It creates
no separate runner, client or production-state file. Native Film controls and MCP
use it through the selected `FilmJobs` facade described below.

The caller supplies a stable opaque `production_id` and a recipe task name.
Reopening that production must reuse its identity; a title, scene name or fresh
random ID on every load is not sufficient. The quote captures a normalized recipe
SHA256 and a task SHA256. The task digest includes the normalized task and the
digests of referenced ancestors, so editing an earlier dependency cannot silently
reuse a later task's old output. References must name earlier tasks. Appending a
new task can reuse unchanged dependencies even though the full recipe digest
changes. Unknown, forward, self and malformed references fail before service work.

`prepare_quote` saves the binding with the exact payload/quote hashes and cost
in the existing [job store](JOB_STORAGE.md#film-task-reservations), before paid
submission. The scope/production/task tuple is reserved atomically across owners.
Any existing attempt, including canceled, failed, prepared and uncertain jobs,
blocks another preparation for that task name. Inspect the saved job for recovery;
a deliberate new take needs a new task name and a fresh quote. A lost write
acknowledgement cannot create a second intent. Restart does not restore a quote or
spending permission. The existing single-use submission and uncertainty rules apply.

References use the saved result manifest's ordered asset IDs after confirmed
remote success. A missing manifest, pending/failed job, changed task or dependency,
other production, cloud-only record or foreign credential/project scope fails.
Local download or Blender application is not required to reuse remote asset IDs;
existing transfer/application failures do not erase a successful remote output.
Literal asset IDs still pass through the selected SDK/model validation and remote
permissions. Upload-task references require the saved association described below.

Recipe text and parameters are not persisted by this binding; the caller must
retain/reload the recipe separately. Quotes are immutable snapshots. A future
view must invalidate its displayed quote when the recipe or production changes
and pass the exact approved request to submission. No recipe field supplies
spending approval, authorizes scene application or infers an API key's project.

## Saved upload tasks

`JobCoordinator.bind_film_upload` associates a recipe's upload task with an
explicitly selected local upload request ID and observed revision. The upload must
already be `imported` in the selected credential scope, with a valid asset ID.
The command does not stage a file, send bytes, initialize/finalize an upload,
refresh remote status or remove sources. Use the existing upload/recovery commands
first. SDK model imports cannot supply asset references.

The shared [job database](JOB_STORAGE.md#film-upload-associations) retains the
association atomically with its task reservation. A model intent and an upload
association cannot reserve the same scope/production/task name. Replacing the
source or changing the task requires a new task name. Repeating the same local
association returns the original record; a new recipe digest from appended tasks
does not overwrite its history. Restart can inspect the association without any
network call or upload replay.

A dependent model quote resolves `$upload-task` or `$upload-task:0` only after
checking the unchanged imported upload again. Pending, failed, uncertain, missing,
stale-revision and foreign-scope uploads fail before estimation. The association
retains the source SHA256, asset ID and kind and rejects a changed observation.
Completed staging cleanup does not invalidate the remote asset; no local byte
read is needed for reuse. Output indexes above zero fail for an upload's single
asset. Existing model schema and service permissions still decide whether that
asset is a valid input for a particular operation.

`JobWorkers` snapshots recipes on the existing queue. `JobSession` captures the
association caller's origin and rejects a changed scene or retired context at
delivery. Repeating an association from another scene returns the same saved
reference to the new reader without retargeting or applying it. The native saved-upload
picker and MCP `bind_film_upload` share this command.

## Native and MCP task controls

Expand **Film tasks** in the Scenario sidebar and choose **Load recipe**. Loading
validates the raw JSON before changing scene data. Reloading preserves the
production identity, including when a title or source filename changes. Save the
blend file to retain both the recipe and identity. **New production** deliberately
starts a separate identity after confirmation; existing saved jobs remain.
Copying a scene or blend file preserves its production identity and task reservations.
Name a new task for another take within that production.

Select one upload task and choose **Use saved upload** to review an already
imported upload. Confirmation records its observed revision and checks the unchanged
scene, recipe, production and selected credentials. Association sends no bytes.
Use the existing reference upload controls first when the source is still local.

For a model task, **Estimate task** resolves its saved dependencies and requests
one exact SDK estimate. **Generate** opens a separate confirmation with the exact
decimal CU cost. Approval consumes the handle before persistence and dispatch.
Recipe edits, a different production/scene or retired credentials reject approval;
the maintenance pump discards obsolete ready estimates, including after frame or
dependency revision changes. Approval checks again before attempting persistence,
so an invalidated price requests a fresh estimate without implying a saved job.
Deleted scene wrappers are
skipped during read-only panel lookup and retired by the pump. Completed quote
and association delivery waits while another scene is current, then rechecks the
unchanged original scene before consuming its completion. Finished tasks are
drained immediately into bounded Film handles, releasing shared session slots
even while delivery waits for that scene. Blender dependency
revision changes, including those emitted during scene activation, still reject
the old quote and require a fresh estimate. **Discard estimate**
releases an unused current quote for repricing. A saved task cannot be spent again,
even with a new quote after an uncertain response or restart.

Current submitted model tasks and associated upload tasks show their saved status
instead of another estimate or association button. A repeated model estimate in
that active context is refused without replacing the saved status. Explicit MCP
upload-association retries still revalidate and return the same saved association;
they never replay an upload.
A different upload or observed revision is rejected before starting another action,
so a conflicting retry does not replace the task's saved association status.
Saved status survives eviction from the 128-action cache. Its separate read-only
projection retains at most the current recipe tasks for each live scene and owns
no worker, approval or reservation authority.

MCP uses `film_recipe` to load/inspect the same scene data and obtain its stable
`production_id`. `estimate_film_task` returns the resolved payload and exact cost;
`approve_film_task` requires that cost verbatim. `discard_film_estimate` releases
an unused approval. `bind_film_upload` requires the context, request and revision
returned by `list_reference_uploads`. Inspection reads local records without
resuming saved jobs. If another scene was current when an MCP response finished,
return to the original scene and inspect again. Inspection completes already-admitted
preparation and exposes an unchanged ready estimate as a `quoted` task, including
its existing `quote_id`, `model_id`, `parameters` and `cu_cost_exact`. Approve that
exact quote or discard it before requesting another. Pending preparation appears
as `quoting` or `binding`; saved upload associations remain inspectable as `bound`.
Inspection never requests a new price, submits, or applies a result, and it omits
quotes whose recipe, scene revision or credential context changed.
See [MCP contracts](MCP.md#local-server-and-mcpscenariocom).

`FilmJobs` owns bounded presentation handles, not an executor or another store.
Approved tasks enter the existing `ModelJobs` polling/download path. Results stay
saved for explicit application through the existing saved-job controls or MCP.
Restarted/paused jobs require explicit recovery; opening Film does not resume or
resubmit them. These controls do not build scenes or assemble a finished film.

## Native shot and timeline primitives

[`film_scene.py`](../scenario/blender/film_scene.py) constructs one new shot scene
from a raw validated recipe. It preserves the current scene, selection, active
object and timeline. A failure removes only newly created geometry, materials,
images, rigs, actions, camera curves and Worlds; no partially built shot is returned.
Repeated builds create separate takes instead of editing an earlier scene.

The builder uses the recipe's frame rate, editorial duration, camera lens/path,
animated camera target, primitive transforms/colors/roles, placeholder motion and
World settings. Camera paths remain editable Bezier curves. Motion keys map
continuously onto the inclusive shot frame range; distinct subframe keys are not
rounded together. It adds local lighting and a ground plane when the plan has no
environment plane. Shot metadata retains the production identity, recipe digest,
editorial/source timing, declared continuity and placeholder legend.

Each hero needs an explicitly selected `HeroSource` containing a saved GLB result
and its download receipt/path. The existing model importer rechecks bounded,
embedded GLB bytes and packs textures. Preflight verifies every source before
mutation, and import rehashes it again. Actors have independent geometry, rigs,
morph data and animation instances. A hero can specify either `width` or `height`
for uniform, proportion-preserving sizing, or omit both to keep its imported size.
Specifying both fails recipe validation before scene creation. Size normalization,
asset orientation, actor transforms, trajectories and imported hold/loop animation
are separate.
Placement measures evaluated rig/morph deformation at the selected initial pose.
Action stops use the same continuous editorial frame mapping as motion keys.
Hold/loop uses the importer's active clip or first stored NLA clip; other clip data
is retained, but this recipe schema has no named-clip selector. Hero reference and
material-task names remain recipe metadata; the builder keeps the GLB's embedded
materials and does not apply a separate material task.

`build_timeline` composes an explicitly supplied complete set of matching live
shot scenes into a new editable scene-strip sequence, with exact editorial order,
frame boundaries and markers. It rejects foreign production/recipe identities,
removed scenes and changed shot timing before creating data. It preserves the
working scene and never replaces an existing sequence.

These are main-thread local primitives, with no SDK, network, paid submission,
file save, activation control or separate job storage. A receipt proves bytes,
not credential ownership or approval. The shared shot command below supplies the
source/destination checks and application claims. Native/MCP scene-building controls
must use that command; timeline approval remains separate. Primitive tests establish
synthetic shot, model and sequence behavior, not visual motion acceptance,
capture/encoding, finishing or export.

## Shared shot application command

`JobSession.film_shots` owns bounded reviews through
[`FilmShotCommands`](../scenario/blender/film_application.py). `inspect` lists
downloaded GLB outputs for the selected scene's recipe and shot. `prepare` requires
an explicit hero-to-output selection with each observed request ID and revision;
it captures the current scene/revision, production identity and exact saved recipe.
Local verification may run in Edit Mode; approval still requires Object Mode
before claiming jobs or building a scene.
`poll` advances local receipt verification on the existing bounded worker queue.
`status` reads a cached review; neither inspection nor preparation builds a scene.

The [source resolver](../scenario/core/jobs/film_sources.py) requires matching
credential scope, production/task identity, model and transitive task digest.
Unrelated editorial changes can reuse an unchanged model task after a fresh review.
Changed task parameters/dependencies, incomplete downloads, uncertain application,
stale revisions and non-GLB selections fail. It never selects an arbitrary first
variant. API keys keep their credential-bound default project; no discovery is
required. Receipt verification is serially admitted per distinct source job, so
hero counts do not require a larger worker pool. A transient other-scene timer
context defers delivery, while finished verification is drained into its bounded
review to release shared session slots. A full queue postpones admission of the
next verification without discarding earlier results. Every later admission
rechecks the recipe, origin and source records; real changes still invalidate
the review. No scene build or paid action is retried by this queue handling.

Separate `approve(review_id)` rechecks the unchanged recipe, destination, source
records, owned verification tickets and GLB bytes. It consumes the review before
claiming every distinct job and before building. Several actors/heroes sharing
one job use one claim; an already applied job uses the existing local model-reuse
claim with the selected asset IDs. The same coordinator/store records the outcome.
A no-hero shot is a local single-use approved action without a fabricated job.

If a later claim fails, known earlier claims are marked failed with no scene build;
the uncertain claim requires inspection. Confirmed full native rollback marks all
known claims failed. Incomplete cleanup retains uncertainty and does not offer a
blind retry. After a successful build, receipt persistence can fail independently:
`retry_receipts` only acknowledges or writes the already attempted outcome and
never calls the builder. It retains the existing shot. Native Undo does not rewind
job receipts; an intentional new take needs another review and claim.

Reviews and receipt handles are owner-local, capped at sixteen, and disappear on
session shutdown. Saved tasks/results survive restart and require fresh destination
review; uncertain durable application remains explicit inspection work. `discard`
retires an unapproved review and drains pending verification without applying it.
After inspecting an uncertain attempt's scene and saved jobs,
`dismiss_uncertain(..., inspected=True)` retires only its review. It refuses
dismissal while a known receipt can still be saved through `retry_receipts`.
Dismissal neither changes saved job state nor repeats scene work: unresolved
application claims still block a fresh review. If a failed claim never reached
storage and the jobs remain eligible, the user can explicitly prepare again
without restarting the session.
There is no new SDK request, download, store, worker pool or UI registration.
Native/MCP presentation, timeline approval and release acceptance remain separate.

## Remaining integration and evidence

Native/MCP scene-building controls, timeline approval, shot capture, media finishing,
provider-specific preparation and final export remain separate work. Keep useful
source capabilities and tests as those paths are connected; do not describe this
helper adoption as a completed Film workflow.

[Shared Film job tests](../tests/unit/test_film_jobs.py) cover atomic competing
reservations, committed-but-unacknowledged writes, uncertain submissions, scope
isolation and transitive dependency changes. Native session tests cover installed
Film quote/submission and changed-scene rejection.
[Upload association tests](../tests/unit/test_film_uploads.py) exercise scope,
imported-state checks, immutable source selection, competing model/upload
reservations and cleanup/restart reuse; native tests verify quote resolution and
late/repeated main-thread delivery.

[Recipe tests](../tests/unit/test_film_plan.py) and
[scene-plan tests](../tests/unit/test_film_scene_plan.py) cover source timing,
transforms, continuity and audio contracts plus API-key default scope, exact
project matching, every foreign-scope dimension, opaque output identifiers,
reference ordering and invalid input rejection. Installed-package regression
checks establish package/runtime compatibility only. Live generation, physical
desktop interaction and human motion/audio review remain #68 acceptance gates.
