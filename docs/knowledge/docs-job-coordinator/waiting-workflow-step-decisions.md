---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.waiting-workflow-step-decisions",
  "title": "Waiting workflow step decisions in the coordinator",
  "description": "Bounded step projection from a retrieved workflow job and one guarded decision per reviewed step.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "waiting-workflow-step-decisions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected workflow_nodes.pending_steps, validate_decision and review_id, JobCoordinator.decide_workflow_node, _decide and _reread, and JobWorkers.decide_workflow_node against the published SDK 2.2.0 flow node model (jobs.retrieve response types, including for-each, loopNodeId, iterationIndex, inputs refs and dependsOn) and the public API reference for the user-selection endpoint and its frozen candidate items. Unit tests use the real SDKAdapter with an httpx MockTransport: approval and ordered selection bodies, project override and omission, reject followed by a canceled retrieval persisting canceled across a reopened store, terminal-on-retrieval sending nothing, changed review_id, missing or finished step and invalid decisions conflicting before any PUT, HTTP 4xx refusals and timeout/5xx/malformed/mismatched acknowledgements each with exactly one PUT and a best-effort retrieval, a lost reject whose retrieval shows canceled, a failed retrieval after acknowledgement, model operations, stale revisions, inactive and deactivated contexts, offline preflight, a concurrent second decision refused locally, a restarted coordinator, and worker snapshots of the picks. Parser tests cover review asset bounds, selection bounds and candidates, loop copies, malformed jobs, ForEach and nested-workflow blocking through every reference kind, unreadable references, unsendable or repeated node IDs, URL exclusion and the reference budget. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No store schema change or decision record exists; cancel_remote stays model-only and a running workflow step cannot be canceled. Private first-party code was not quoted. Re-reviewed on 2026-10-10 after the parser began treating a node type that the API reference does not list (custom-model, for-each, generate-prompt, list, logic, model, remove-background, transform, user-approval, user-selection and workflow) like a loop: a selection it reads is blocked as loop, and unreadable references in a flow containing one block every selection; parser tests cover each listed non-loop type, an unlisted reader and an unlisted node that does not read the selection. Re-reviewed on 2026-10-10 after a live check showed retrieved job flows listing inputs only on user-selection nodes and no dependsOn, so a selection feeding a ForEach loop was offered: workflow_nodes now treats a job node with neither field as having unknown links, reads links from the workflow definition through definition_links and uses them only when the definition matches the job (same workflow, updatedAt not after createdAt, same node IDs and types, agreement with the job's own links, other nodes ForEach copies of body nodes), blocks a selection as unverified when links stay unknown in a flow that may loop, maps a copy's dependencies to its iteration and reports links_complete; JobCoordinator._observe_remote reads the definition once per waiting period through SDKAdapter.workflow (SDK workflows.retrieve), attaches it to the snapshot and drops it once no step waits, and _decide projects with the same links. New tests/unit/test_workflow_step_links.py uses live-shaped flows (approval gate, selection into and after a ForEach, copies, mismatching or edited definitions, unreadable definitions); decision tests cover one definition read per waiting period, failures retried and failing closed, a selection into a loop refused before any PUT with or without the definition, a selection after a loop sent with it, a review made with links conflicting when they are unreadable, and an approval bound to its linked review assets. Live read-only checks confirmed the definition shape for public ForEach workflows only; definitions with approval or selection steps follow the SDK model and are covered offline.",
    "sources": {
      "scenario/core/jobs/workflow_nodes.py": "81a15c7f5bc51c74dd94d8abe1f5e1d44d9db12fdea35d79fb2c967f3e65f261",
      "scenario/core/jobs/coordinator.py": "4c7a7242c8f295650cd548bddd1db0bfe197da487998f2897de03a78830a4882",
      "scenario/core/jobs/workers.py": "f0b9c87f893c58bbe89604a6187c13fca8c3dbcfc50f63bbfcf24455bd54a375",
      "tests/unit/test_workflow_nodes.py": "6556b51d3750e58c0be73596829e52f4ca448121504cab0c3900831ab1c1aacd",
      "tests/unit/test_workflow_decisions.py": "bed926329df85c217701d8bc0141d5645d98cf5d32ee9372de4644404a9cac2d",
      "scenario/core/api/sdk_adapter.py": "82d37a4f38b72726ca0060ee0cf66e769cec758f96a166aeeed92580d3fe0a08",
      "tests/unit/test_workflow_step_links.py": "3dbf4b8351072c6be1ada09a7a92e11ba0a273e3c307b339a274f3779af8ef61",
      "tests/unit/test_scenario_sdk_contract.py": "76503120843177b289f1957790f73eb89dd59679a697befdd317e6b2f13dac0d"
    }
  }
}
---

# Waiting workflow step decisions in the coordinator

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
