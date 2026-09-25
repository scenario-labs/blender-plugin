# Known limitations

This page distinguishes inspected code limitations from unverified service or
platform behavior. See the [audit](maintenance/backlog.md) for the disposition
of older reports and the [runtime map](architecture/runtime.md) for integration
boundaries. No paid or live acceptance is implied by this documentation.

## Runtime and authentication

- UI and local MCP paid generation still use the prototype client and manager. Shared SDK,
  persistence, transfer and origin-guard components need runtime integration
  ([#64](https://github.com/scenario-labs/blender-plugin/issues/64),
  [#65](https://github.com/scenario-labs/blender-plugin/issues/65)).
- Credentials use one explicitly selected pair (saved Blender preferences by
  default, environment only when selected). Shared job/account/project scope
  integration remains #65. Browser sign-in in
  [#67](https://github.com/scenario-labs/blender-plugin/issues/67) is deferred.
- Trained/custom-model discovery and routing remain incomplete
  ([#97](https://github.com/scenario-labs/blender-plugin/issues/97)).

## Creation and scene application

- MCP generation does not yet share the UI's render-lane decoration and full
  preparation/approval path. Shared commands are tracked in #65.
- Reversible mesh and panoramic World application exist as explicit synchronous
  primitives. Full generation/history integration remains
  [#99](https://github.com/scenario-labs/blender-plugin/issues/99) and
  [#98](https://github.com/scenario-labs/blender-plugin/issues/98).
- Multi-object mesh export combines the selection. Safe in-place multi-object
  editing needs separate acceptance under #99.
- Prompt helpers can make paid calls, including an LLM fallback when Prompt
  Spark yields no usable text. Historical price figures are not current quotes.
- Video-to-motion and speech-to-text workflows remain an explicit capability
  request in [#190](https://github.com/scenario-labs/blender-plugin/issues/190);
  model tags alone do not establish supported input and result handling.

## Interface and capture

- The prototype composer and sidebar expose different controls. Model schema
  loading, long-prompt editing and compact/expanded behavior need the native
  acceptance in [#66](https://github.com/scenario-labs/blender-plugin/issues/66).
- Viewport screenshots and OpenGL capture require a GUI. Automated GUI probes
  can take keyboard focus; follow the isolated-profile validation procedure.
- Downloaded audio has an explicit local PCM-WAV waveform preview in Generations.
  It uses the existing result record/file selection, not the durable verified
  result identity planned in #65. Compressed audio previews, the shared compact/
  expanded result UI and human audio review remain #189, #66 and #68 work.
  See the [supported preview limits](USER_GUIDE.md#audio).
- Audio reads and metadata checks run in at most two tracked workers; Blender only
  displays its captured snapshot after checking the selected record and context.
  The preview does not monitor later external file changes. Cancellation discards
  late completion; it cannot interrupt an operating-system filesystem call.
  A spare worker lets another preview proceed while one canceled read is stuck.
  Loading expires after 30 seconds, checked by Blender's timer. If both workers
  remain occupied, a new preview times out with retry/restart guidance; capacity
  becomes available only when a worker actually exits. The UI remains usable.
  Terminal previews check context invalidation once per second rather than at
  the loading timer's ten checks per second.
- Prompt helpers lack an explicit generic/model-contextual Spark preference
  ([#188](https://github.com/scenario-labs/blender-plugin/issues/188)).
- Capture timing follows scene settings; native dialogs use Blender's theme
  rather than the custom composer drawing.

## Verification

Offline contracts establish the behavior of fixtures and local state machines.
Live OAuth acceptance, provider behavior, full UI/MCP parity and supported
platform interaction remain separate gates in
[#68](https://github.com/scenario-labs/blender-plugin/issues/68).
Inherited historical reports must be reproduced before being called current
bugs. Passing a knowledge check establishes structure and freshness signals,
not prose truth or runtime correctness.
