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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the published SDK 2.2.0 workflows resource (user_approval signature, typed-required project_id, omit handling, raw-response wrapper, no user_selection), its path-segment encoding and low-level put/retry options, the public API reference for PUT /workflows/{workflowId}/user-selection, including its default selection maximum of 100, and SDK issue #33. Offline SDK and adapter tests cover explicit actions, 1 to 100 ordered unique indices within the exact JSON integer range, body-only node IDs, printable-only IDs that reject control and format characters and lone surrogates before serialization, project override only, selected Basic/Bearer auth despite ambient values, permission/lifetime, single attempts (the selection fallback also on an SDK client configured to retry) with status-carrying sanitized errors that survive copy and pickle, and matching acknowledgements; one installed bundle test exercises the same path in Blender. Re-reviewed after rebasing on the adapter's credential, project and rate-limit status text (#352) and the model-read AdapterUnavailable (#357): AdapterStatusError now carries that text and keeps it through copy and pickle, and an approval sent with the SDK omit sentinel counts as carrying no project, so its 403 never names the Project ID. Tests cover the HTTP 429 text and a 403 with and without an override for every decision kind. The documented outcome contract treats every non-status AdapterError, including pre-send offline and closed refusals, as uncertain; no distinct pre-dispatch error type exists. Omitting projectId for API-key decisions, server handling of concurrent or repeated decisions, loop-scoped rejection and spend after a decision are not live-verified. No coordinator, UI or MCP caller, durable decision record, ForEach spend guard or general workflow cancellation exists. Private first-party code was not quoted.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "82d37a4f38b72726ca0060ee0cf66e769cec758f96a166aeeed92580d3fe0a08",
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "tests/unit/test_scenario_sdk_contract.py": "3b126ec239e38d0e5482c15fafdb93ab3326418e0b3ae966ded3ea3d90d75070",
      "tests/unit/test_sdk_extensions.py": "2e87d523c0836944b0ac5ecc05cfd4edb579a72f7b511bd855b0e59f13550b70",
      "tests/unit/test_sdk_adapter.py": "37e9dcb823c8d199794cddc19c809fbceff6c99eae2823a18b401ecd5df9fbbf",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# Workflow step decisions in the shared SDK adapter

Evidence for [the canonical document](../../SDK_ADOPTION.md).
