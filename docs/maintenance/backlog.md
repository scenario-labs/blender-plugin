# Documentation and issue disposition

This is an inspection record, not a release acceptance report. Source locations
are linked in the [runtime map](../architecture/runtime.md) and in the evidence
registry. Follow the [knowledge review procedure](knowledge.md) when updating it.

## Existing documentation issues

| Issue | Disposition in this foundation |
| --- | --- |
| [#4](https://github.com/scenario-labs/blender-plugin/issues/4) | Canonical root instructions, detailed required guides and path adapters are present. #107 established the shared symlink/skill layout. Historical Blender 4.2, root CLAUDE import, command layout and unconditional test requirements must be reconciled before closure; no fresh Claude session verification is claimed. |
| [#6](https://github.com/scenario-labs/blender-plugin/issues/6) | Historical design/plans moved to engineering, labeled and scrubbed of personal paths, session identifiers and spend anecdotes. Broader source-comment/generator cleanup and full-tree acceptance remain outside this documentation change. |
| [#25](https://github.com/scenario-labs/blender-plugin/issues/25) | Every legacy BUGS.md item has a disposition below. The old report is retired to Git history; exact issue creation/project metadata requirements are not claimed complete. |
| [#2](https://github.com/scenario-labs/blender-plugin/issues/2), [#13](https://github.com/scenario-labs/blender-plugin/issues/13) | Navigation and misleading local notes receive targeted corrections. The complete public README and current user-guide rewrite still need their own acceptance. |
| [#48](https://github.com/scenario-labs/blender-plugin/issues/48) | Existing setup/release docs are indexed; this does not complete all contribution, licensing and release-policy requirements. |
| [#47](https://github.com/scenario-labs/blender-plugin/issues/47), [#52](https://github.com/scenario-labs/blender-plugin/issues/52) | External URL monitoring and generated MCP reference are separate work. Local knowledge checks implement neither. |
| [#54](https://github.com/scenario-labs/blender-plugin/issues/54) | Shared skills and adapters exist; hooks, settings and client templates retain their own scope. |

## Legacy limitations audit

The former BUGS.md mixed bugs, design boundaries and superseded
observations. This table preserves a disposition for each bullet without copying
private anecdotes or treating old live observations as current service contracts.

| Original subject | Current evidence and disposition |
| --- | --- |
| Native tests use real extension state | The current [native runner](../../tools/test_blender.py) and [profile helpers](../../tools/blender_env.py) own disposable profiles and verify installed contents. The original runner claim is superseded; direct ad hoc invocations must still isolate profiles. |
| Environment overrides preferences | Still present in [resolve_credentials](../../scenario/core/config.py); #67 owns active account integration. The SDK adapter has stronger isolation, but is not yet the active prototype client. |
| Slow non-curated schema loading | [generation](../../scenario/blender/generation.py) and [parameter UI](../../scenario/blender/params_ui.py) retain async loading; failure/retry UX belongs with #66. |
| Single-line prompt editing | Current [composer](../../scenario/blender/composer/modal.py) is a custom editor. Long text and native interaction require #66 acceptance; do not preserve the older editor-button claim as a tested fact. |
| GUI-only capture | [Capture](../../scenario/blender/capture.py) and [MCP scene tools](../../scenario/mcp/tools_blender.py) use viewport/OpenGL behavior; this limitation remains. |
| No project switcher | #67 remains open. An optional developer project ID and adapter project scope do not implement a UI account/project switcher. |
| GUI probes take focus | [Probe script](../../tools/gui_screenshot.py) starts native interaction and sets a generation guard. Focus interference remains a reason to use controlled GUI validation; historical spend anecdotes are removed. |
| MCP bypasses render prompt decoration | Compare [MCP generation](../../scenario/mcp/tools_scenario.py) with [render lanes](../../scenario/blender/render_lanes.py); #65 owns convergence. |
| Spark generic mode only | Superseded by the model ID passed in [prompt_tools](../../scenario/blender/prompt_tools.py). Fixed historical prices are not service contracts. |
| Model picker fallback | [Model picker](../../scenario/blender/model_picker.py) and [property enum handling](../../scenario/blender/props.py) retain fallback behavior; treat as an implementation detail and cover it during #66, not a new defect without reproduction. |
| Shot markers and aim behavior | [Shot planner](../../scenario/blender/shot_planner.py) implements camera markers and aiming. This is a design behavior, not evidence of a broken feature. |
| Selection exported as one mesh | [Mesh export](../../scenario/blender/mesh_export.py) exports the selection; #99 must establish safe target/result identity for edits. |
| Composer lacks sidebar lanes | [Composer drawing](../../scenario/blender/composer/draw.py) and [properties](../../scenario/blender/props.py) define different interfaces; #66 owns compact/expanded convergence. |
| Audio waveform absent | [Audio application](../../scenario/blender/apply_audio.py) and [history](../../scenario/blender/history.py) provide playback/sequencer paths; waveform UX remains unaccepted, to triage under #66/#68. |
| Prompt helper pricing | Model-contextual Spark and fallback exist in prompt_tools. Historical numerical prices are retired; shared exact estimate/approval handling remains #65. |
| Motion, speech-to-text and standalone text lanes | Existing lane choices in props do not establish these product workflows. Capability decisions belong with #64 and view acceptance with #66; do not invent delivery commitments. |
| Categories from names/tags | [model_filter](../../scenario/core/api/model_filter.py) contains heuristics. #97 owns catalog acceptance; provider taxonomy needs current evidence. |
| Native versus custom theme | [UI style](../UI_STYLE.md) explains Blender widgets and custom compositor presentation. This is a design boundary, not a runtime bug. |
| Spark returns unusable asset references | The [Spark parser](../../scenario/core/api/spark.py) and prompt_tools reject unusable answers and use a fallback. The old provider-specific live failure is not freshly reproduced; shared spending semantics remain #65. |
| Capture FPS follows scene | [capture.py](../../scenario/blender/capture.py) derives capture timing from scene settings. Separate capture controls require explicit product scope under #66. |

## Review limits and next work

No issue is closed solely because it has an entry in this table. Old acceptance
criteria sometimes encode superseded dependency, platform, directory or test
policies; reconcile them explicitly in the issue before marking the remaining
scope complete. No new runtime behavior, live provider proof, human approval or
automatic code-retirement decision is claimed here.

The next useful documentation slices are the public README/user guide, generated
MCP reference and external link checker. A scheduled model-generated updater is
deferred until maintainers choose its review behavior and spending limits.
