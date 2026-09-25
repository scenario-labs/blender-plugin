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
- Audio preview lacks a waveform display
  ([#189](https://github.com/scenario-labs/blender-plugin/issues/189)). Prompt
  helpers lack an explicit generic/model-contextual Spark preference
  ([#188](https://github.com/scenario-labs/blender-plugin/issues/188)).
  Capture timing follows scene settings;
  native dialogs use Blender's theme rather than the custom composer drawing.
  These are existing interface boundaries, not claims that new controls exist.

## Verification

Offline contracts establish the behavior of fixtures and local state machines.
Live OAuth acceptance, provider behavior, full UI/MCP parity and supported
platform interaction remain separate gates in
[#68](https://github.com/scenario-labs/blender-plugin/issues/68).
Inherited historical reports must be reproduced before being called current
bugs. Passing a knowledge check establishes structure and freshness signals,
not prose truth or runtime correctness.
