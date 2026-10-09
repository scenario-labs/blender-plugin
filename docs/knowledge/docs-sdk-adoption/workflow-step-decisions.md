---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.workflow-step-decisions",
  "title": "Workflow step decisions in the shared SDK adapter",
  "description": "Approval and selection decisions for waiting workflow steps, including the user-selection fallback.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "workflow-step-decisions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the published SDK 2.2.0 workflows resource (user_approval signature, typed-required project_id, omit handling, raw-response wrapper, no user_selection), its path-segment encoding and low-level put/retry options, the public API reference for PUT /workflows/{workflowId}/user-selection, including its default selection maximum of 100, and SDK issue #33. Offline SDK and adapter tests cover explicit actions, 1 to 100 ordered unique indices within the exact JSON integer range, body-only node IDs, printable-only IDs that reject control and format characters and lone surrogates before serialization, project override only, selected Basic/Bearer auth despite ambient values, permission/lifetime, single attempts (the selection fallback also on an SDK client configured to retry) with status-carrying sanitized errors that survive copy and pickle, and matching acknowledgements; one installed bundle test exercises the same path in Blender. The documented outcome contract treats every non-status AdapterError, including pre-send offline and closed refusals, as uncertain; no distinct pre-dispatch error type exists. Omitting projectId for API-key decisions, server handling of concurrent or repeated decisions, loop-scoped rejection and spend after a decision are not live-verified. No coordinator, UI or MCP caller, durable decision record, ForEach spend guard or general workflow cancellation exists. Private first-party code was not quoted.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "1104fbb8a78b13deafd3c5098d932da39a8fdfa9ee38707e7a96452ec72877a5",
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "tests/unit/test_scenario_sdk_contract.py": "a23b96b3792abb83fbca65f0755e7d7c33cec08cd3f739f8cf0dc67e16ffc026",
      "tests/unit/test_sdk_extensions.py": "4770f482ae18aa01aea6ffb5525d06c7b15a48143901acb24eb9e438d83fb51b",
      "tests/unit/test_sdk_adapter.py": "5ed5648c2487ff6a4ffdf0f4ef8cde0fd20b1363c5ff66d9000e932229fdb23c",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# Workflow step decisions in the shared SDK adapter

Evidence for [the canonical document](../../SDK_ADOPTION.md).
