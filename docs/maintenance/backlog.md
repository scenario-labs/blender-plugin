# Documentation and issue disposition

This is an inspection record, not a release acceptance report. Source locations
are linked in the [runtime map](../architecture/runtime.md) and in the evidence
registry. Follow the [knowledge review procedure](knowledge.md) when updating it.

## Existing documentation issues

| Issue | Disposition in this foundation |
| --- | --- |
| [#4](https://github.com/scenario-labs/blender-plugin/issues/4) | Closed after canonical root instructions, required guides, shared skills/path adapters and fresh CLI instruction-context verification. Historical Blender 4.2, root CLAUDE import and unconditional test requirements are superseded by the current contract. |
| [#6](https://github.com/scenario-labs/blender-plugin/issues/6) | The sanitized prototype design and plans are retired from the working tree; Git retains their history. Current instructions and useful architecture rationale live in the maintained guides. Personal product-decision comments and report-generator punctuation were cleaned up. Required Studio author credits remain under the current attribution policy; a historical blanket first-name exclusion does not override that policy. |
| [#25](https://github.com/scenario-labs/blender-plugin/issues/25) | Every legacy report has a current disposition below. Resolved reports stay resolved; existing integration issues retain their scope. The distinct remaining feature requests are filed and the current follow-ups have issue types and project Priority/Effort triage. |
| [#2](https://github.com/scenario-labs/blender-plugin/issues/2), [#13](https://github.com/scenario-labs/blender-plugin/issues/13) | The public README and current guide refresh are merged; both issues are closed. Screenshot optimization and full supported-platform/runtime acceptance remain separate under #14 and #68. |
| [#48](https://github.com/scenario-labs/blender-plugin/issues/48) | Contributor setup, public-content rules, inbound licensing, attribution, issue triage and release version/override controls are documented against current tooling. Historical direct-profile installs, blanket dependency/originality bans and assumed hosted publication are superseded by the canonical guides. Optional local hooks are implemented; hosted handbook delivery retains its separate gate. |
| [#47](https://github.com/scenario-labs/blender-plugin/issues/47), [#52](https://github.com/scenario-labs/blender-plugin/issues/52) | Both are closed: the generated MCP reference/native tool contract and hosted external-link monitoring have their own verified checks. [The contribution guide](../development/contributions.md#link-check) describes the link scanner and scheduled reporter; local knowledge checks remain separate. |
| [#54](https://github.com/scenario-labs/blender-plugin/issues/54) | Shared skills and adapters exist; hooks, settings and client templates retain their own scope. |

## Legacy limitations audit

The retired prototype report mixed bugs, design boundaries and superseded
observations. This table preserves a disposition for each bullet without copying
private anecdotes or treating old live observations as current service contracts.

| Original subject | Current evidence and disposition |
| --- | --- |
| Native tests use real extension state | The current [native runner](../../tools/test_blender.py) and [profile helpers](../../tools/blender_env.py) own disposable profiles and verify installed contents. The original runner claim is superseded; direct ad hoc invocations must still isolate profiles. |
| Environment overrides preferences | Resolved by explicit source selection in [resolve_credentials](../../scenario/core/config.py): preferences are the default, environment requires opt-in, and incomplete pairs cannot mix. Shared account/project job scope still belongs to #65; OAuth is deferred. |
| Slow non-curated schema loading | [Generation](../../scenario/blender/generation.py) and [parameter UI](../../scenario/blender/params_ui.py) retain async loading. Panel/render-lane controls display loading or schema errors without a dedicated selected-model retry action; failure/retry UX belongs with [#66](https://github.com/scenario-labs/blender-plugin/issues/66). |
| Single-line prompt editing | The current [composer](../../scenario/blender/composer/modal.py) submits on Enter, including modified Enter. Multiline editing and the associated focus/keyboard contract remain within [#66](https://github.com/scenario-labs/blender-plugin/issues/66); the removed editor-button report is not a current defect. |
| GUI-only capture | [Capture](../../scenario/blender/capture.py) and [MCP scene tools](../../scenario/mcp/tools_blender.py) use viewport/OpenGL behavior; this limitation remains. |
| No project switcher | [Preferences](../../scenario/prefs.py) now expose an optional Project ID for the explicitly selected API-key source. Blank uses credential-bound server scope; no discovery selection is required. Live permissions and native setup/switching acceptance remain #65/#66/#68. Browser OAuth remains deferred under #67. |
| GUI probes take focus | [Probe script](../../tools/gui_screenshot.py) starts native interaction and sets a generation guard. Focus interference remains a reason to use controlled GUI validation; historical spend anecdotes are removed. |
| MCP bypasses render prompt decoration | Resolved at the command boundary: [MCP generation](../../scenario/mcp/tools_scenario.py) uses the native [render request builder](../../scenario/blender/render_commands.py), including decoration and prepared references. Spark preparation retains its separate quote/approval before final render pricing. Live and desktop parity still need #65/#68 acceptance. |
| Spark generic mode only | Superseded by the model ID passed in [prompt_tools](../../scenario/blender/prompt_tools.py). An explicit generic/model-contextual preference is a separate request in [#188](https://github.com/scenario-labs/blender-plugin/issues/188). Fixed historical prices are not service contracts. |
| Model picker fallback | [Model picker](../../scenario/blender/model_picker.py) and [property enum handling](../../scenario/blender/props.py) retain fallback behavior; treat as an implementation detail and cover it during #66, not a new defect without reproduction. |
| Shot markers and aim behavior | [Shot planner](../../scenario/blender/shot_planner.py) implements camera markers and aiming. This is a design behavior, not evidence of a broken feature. |
| Selection exported as one mesh | [Mesh export](../../scenario/blender/mesh_export.py) exports the selection; #99 must establish safe target/result identity for edits. |
| Composer lacks sidebar lanes | [Composer drawing](../../scenario/blender/composer/draw.py) and [properties](../../scenario/blender/props.py) define different interfaces; #66 owns compact/expanded convergence. |
| Audio waveform absent | [Local audio preview](../../scenario/blender/audio_preview.py) renders a downloaded result's waveform without playback or service calls, decoding WAV, MP3, Ogg, FLAC and AAC in an [offline Blender process](../RESULT_PREVIEWS.md#offline-audio-envelopes). Saved shared results get receipt-keyed envelopes on the preview lane, not yet drawn by any view. Shared-view integration and complete [#189](https://github.com/scenario-labs/blender-plugin/issues/189) acceptance remain separate; native playback and listening acceptance remain #68. |
| Prompt helper pricing | [PromptJobs](../../scenario/blender/prompt_jobs.py) uses shared SDK quotes, exact approval and durable submission for New, Rewrite and Translate. Failure stops with saved-job guidance; no automatic paid LLM fallback remains. Historical numerical prices are retired; live acceptance remains #65/#68. |
| Motion, speech-to-text and standalone text lanes | Existing lane choices in props do not establish these product workflows. Video-to-motion and speech-to-text input/result paths are tracked in [#190](https://github.com/scenario-labs/blender-plugin/issues/190), subject to verified SDK/provider support. Broader capability adoption remains #64 and view acceptance #66; no standalone text workflow is implied. |
| Categories from names/tags | [model_filter](../../scenario/core/api/model_filter.py) contains heuristics. #97 owns catalog acceptance; provider taxonomy needs current evidence. |
| Native versus custom theme | [UI style](../UI_STYLE.md) explains Blender widgets and custom compositor presentation. This is a design boundary, not a runtime bug. |
| Spark returns unusable asset references | The [shared text-result reader](../../scenario/core/jobs/results.py) rejects unusable asset references and retrieves complete bounded text through the SDK. The old Spark client and partial-preview fallback are removed. The provider-specific live failure is not freshly reproduced; live acceptance remains #65/#68. |
| Capture FPS follows scene | [capture.py](../../scenario/blender/capture.py) derives capture timing from scene settings. Separate capture controls require explicit product scope under #66. |

## Review limits and next work

The separate Windows/Linux GUI verification request is already covered by
[#68](https://github.com/scenario-labs/blender-plugin/issues/68): actual desktop
focus/input/DPI/audio acceptance on the supported Blender matrix. Headless tests
do not satisfy that requirement; the old Blender 4.x labels are superseded by
the approved Blender 5.0/5.1/5.2 matrix.

The current follow-up set is #64, #65, #66, #68, #97, #99 and #188 through #190.
Their issue types and project Priority/Effort fields are recorded in the project;
#31 is closed for the implemented portable-tooling foundation; it does not establish every desktop/media acceptance gate. The historical request
for a fixed number of newly filed issues is reconciled with resolved credential
and isolation defects and existing integration owners. Do not reopen fixed bugs
or duplicate an existing issue to meet that historical count. Beginner and
help-wanted labels reflect the actual task's suitability; the old seeding quota
does not justify presenting broad runtime or spending-boundary work as beginner
tasks.

Filing and triage do not implement these features or establish new runtime, live
provider or human acceptance. The linked feature and integration issues remain
open for their own complete acceptance.

External link monitoring is implemented and accepted under closed #47, as a separate documentation check.
A scheduled model-generated updater is
deferred until maintainers choose its review behavior and spending limits.
