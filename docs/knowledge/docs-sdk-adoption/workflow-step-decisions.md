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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the published SDK 2.2.0 workflows resource (user_approval signature, typed-required project_id, omit handling, raw-response wrapper, no user_selection), its path-segment encoding and low-level put/retry options, the public API reference for PUT /workflows/{workflowId}/user-selection and SDK issue #33. Offline SDK and adapter tests cover explicit actions, ordered unique indices, body-only node IDs, project override only, selected Basic/Bearer auth despite ambient values, permission/lifetime, single attempts with status-carrying sanitized errors and matching acknowledgements; one installed bundle test exercises the same path in Blender. Omitting projectId for API-key decisions, server compare-and-swap, loop-scoped rejection and spend after a decision are not live-verified. No coordinator, UI or MCP caller, durable decision record, ForEach spend guard or general workflow cancellation exists. Private first-party code was not quoted.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "3c8615df80c9beb688f689c4ab6fd14f2bc49640c72d2ea4a842aba7d1b6dc7e",
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "tests/unit/test_scenario_sdk_contract.py": "a23b96b3792abb83fbca65f0755e7d7c33cec08cd3f739f8cf0dc67e16ffc026",
      "tests/unit/test_sdk_extensions.py": "58bc9de1ed02dd4ae4b36645d3e87858af593a466db80411d96fcf878d0522ac",
      "tests/unit/test_sdk_adapter.py": "fa5e30160d16cba202045aa2f42533468f66098d77e00cfc429e1347ae7d7457",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# Workflow step decisions in the shared SDK adapter

Evidence for [the canonical document](../../SDK_ADOPTION.md).
