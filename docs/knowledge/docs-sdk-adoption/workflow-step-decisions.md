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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the published SDK 2.2.0 workflows resource (user_approval signature, typed-required project_id, omit handling, raw-response wrapper, no user_selection), its path-segment encoding and low-level put/retry options, the public API reference for PUT /workflows/{workflowId}/user-selection, including its default selection maximum of 100, and SDK issue #33. Offline SDK and adapter tests cover explicit actions, 1 to 100 ordered unique indices within the exact JSON integer range, body-only node IDs, printable-only IDs that reject control and format characters and lone surrogates before serialization, project override only, selected Basic/Bearer auth despite ambient values, permission/lifetime, single attempts (the selection fallback also on an SDK client configured to retry) with status-carrying sanitized errors that survive copy and pickle, and matching acknowledgements; one installed bundle test exercises the same path in Blender. Re-reviewed after rebasing on the adapter's credential, project and rate-limit status text (#352) and the model-read AdapterUnavailable (#357): AdapterStatusError now carries that text and keeps it through copy and pickle, and an approval sent with the SDK omit sentinel counts as carrying no project, so its 403 never names the Project ID. Tests cover the HTTP 429 text and a 403 with and without an override for every decision kind. The documented outcome contract treats every non-status AdapterError, including pre-send offline and closed refusals, as uncertain; no distinct pre-dispatch error type exists. Omitting projectId for API-key decisions, server handling of concurrent or repeated decisions, loop-scoped rejection and spend after a decision are not live-verified. Re-reviewed on 2026-10-10 for the first caller: JobCoordinator.decide_workflow_node calls workflow_decision once per reviewed step after retrieving the job, maps an HTTP 4xx AdapterStatusError to a refusal, a ValueError to nothing sent and every other failure to an uncertain outcome, and blocks choosing items for a selection that feeds a ForEach loop or nested workflow; unit tests drive it through this adapter with a mock transport. No UI or MCP control, durable decision record or general workflow cancellation exists. The test_scenario_sdk_contract.py drift since the earlier review (the remote progress contract) was not re-reviewed here. Private first-party code was not quoted. Re-reviewed on 72723f02 after rebasing on the asset organization writes (#355): its collection and asset reads use the same _request status mapping, while its writes use a separate _write path that raises WriteRejected or WriteUncertain and never reaches workflow_decision; the shared _identifier now also rejects lone surrogates, which _printable already refused for decision IDs, and _json reports a too deeply nested acknowledgement as invalid JSON, which the decision contract already treats as an unknown outcome. The decision path, its adapter and extension tests and its contract-test assertions are unchanged; 5674 offline unit tests pass with the known SDK authentication xfail. The native suite was not rerun for this rebase.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "f541b2eaa8ea8dbdcb9636a161961f33239b4f3febe63ca1a1a54e5e57071628",
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "tests/unit/test_scenario_sdk_contract.py": "f95d78222688a19c98ade0595afc24375e2d38784e58a6a557b67dff64a2e4fd",
      "tests/unit/test_sdk_extensions.py": "2e87d523c0836944b0ac5ecc05cfd4edb579a72f7b511bd855b0e59f13550b70",
      "tests/unit/test_sdk_adapter.py": "37e9dcb823c8d199794cddc19c809fbceff6c99eae2823a18b401ecd5df9fbbf",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2",
      "scenario/core/jobs/coordinator.py": "748c445070b9c3430a6ee28c9dbed94e2463b6703e076c83200cfdb36e843cfa",
      "tests/unit/test_workflow_decisions.py": "9022e540c17121895aa93826922ac59e3e4ddfe508701931896e2f86e98eeeda"
    }
  }
}
---

# Workflow step decisions in the shared SDK adapter

Evidence for [the canonical document](../../SDK_ADOPTION.md).
