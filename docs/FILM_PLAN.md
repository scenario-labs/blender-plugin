# Film recipe contracts

The adopted [Film recipe helpers](../scenario/core/scene/film_plan.py) and
[scene-plan helpers](../scenario/core/scene/film_scene_plan.py) preserve bounded
planning, editorial timing, continuity declarations and reference ordering from
the selected Studio source. They are pure Python: they do not open files, contact
Scenario, submit jobs or mutate Blender.

This is the input contract for the remaining Film integration under #64/#65.
There is no active Film UI or MCP command yet. Passing these contracts does not
establish a Film generation journey or satisfy the [release gate](maintenance/release-plan.md).

## Recipe and timing validation

`validate_film_plan` returns a new normalized recipe. It rejects non-finite or
non-JSON values, cycles, recipes exceeding two million UTF-8 JSON bytes, unknown
structural keys, invalid transforms and ambiguous timing. It supports one to
fifty shots, at most three hundred upload/model tasks, and at most fifteen minutes
of editorial duration. Tasks have explicit names; another take needs another
task name. Model parameter objects are data and still require the selected
SDK model schema before a quote.

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

The future coordinator must construct these observations from its scoped saved
jobs/uploads after checking their state. The helper does not read storage or
certify completion of a caller-supplied observation. Resolved parameters still
need a fresh exact quote, explicit approval and a durable task/submission binding;
resolution is not spending authorization. No separate Film runner, client or
production-state database is introduced here.

## Remaining integration and evidence

Next integration must persist recipe/task identity with shared jobs before
spending, retain ambiguous submission state without retry, derive references from
verified scoped saved outputs, and expose the same preparation/approval commands
to native views and local MCP. Scene construction, shot capture, media finishing,
provider-specific preparation and final export remain separate work. Keep useful
source capabilities and tests as those paths are connected; do not describe this
helper adoption as a completed Film workflow.

[Recipe tests](../tests/unit/test_film_plan.py) and
[scene-plan tests](../tests/unit/test_film_scene_plan.py) cover source timing,
transforms, continuity and audio contracts plus API-key default scope, exact
project matching, every foreign-scope dimension, opaque output identifiers,
reference ordering and invalid input rejection. Installed-package regression
checks establish package/runtime compatibility only. Live generation, physical
desktop interaction and human motion/audio review remain #68 acceptance gates.
