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
    "limits": "Inspected workflow_nodes.pending_steps, validate_decision and review_id, JobCoordinator.decide_workflow_node, _decide and _reread, and JobWorkers.decide_workflow_node against the published SDK 2.2.0 flow node model (jobs.retrieve response types, including for-each, loopNodeId, iterationIndex, inputs refs and dependsOn) and the public API reference for the user-selection endpoint and its frozen candidate items. Unit tests use the real SDKAdapter with an httpx MockTransport: approval and ordered selection bodies, project override and omission, reject followed by a canceled retrieval persisting canceled across a reopened store, terminal-on-retrieval sending nothing, changed review_id, missing or finished step and invalid decisions conflicting before any PUT, HTTP 4xx refusals and timeout/5xx/malformed/mismatched acknowledgements each with exactly one PUT and a best-effort retrieval, a lost reject whose retrieval shows canceled, a failed retrieval after acknowledgement, model operations, stale revisions, inactive and deactivated contexts, offline preflight, a concurrent second decision refused locally, a restarted coordinator, and worker snapshots of the picks. Parser tests cover review asset bounds, selection bounds and candidates, loop copies, malformed jobs, ForEach and nested-workflow blocking through every reference kind, unreadable references, unsendable or repeated node IDs, URL exclusion and the reference budget. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No store schema change or decision record exists; cancel_remote stays model-only and a running workflow step cannot be canceled. Private first-party code was not quoted.",
    "sources": {
      "scenario/core/jobs/workflow_nodes.py": "94a38896e6331e6dc993a5a83ecdb7b740ab5f60897bab73e7f45f4dbcade4d2",
      "scenario/core/jobs/coordinator.py": "748c445070b9c3430a6ee28c9dbed94e2463b6703e076c83200cfdb36e843cfa",
      "scenario/core/jobs/workers.py": "f0b9c87f893c58bbe89604a6187c13fca8c3dbcfc50f63bbfcf24455bd54a375",
      "tests/unit/test_workflow_nodes.py": "8039759f855a63d12f033a1fd3f178b6ba1f1dfd1153f3e3393c9994233c5f7b",
      "tests/unit/test_workflow_decisions.py": "9022e540c17121895aa93826922ac59e3e4ddfe508701931896e2f86e98eeeda",
      "scenario/core/api/sdk_adapter.py": "82d37a4f38b72726ca0060ee0cf66e769cec758f96a166aeeed92580d3fe0a08"
    }
  }
}
---

# Waiting workflow step decisions in the coordinator

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
