---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.waiting-workflow-steps",
  "title": "Waiting workflow steps in the shared session",
  "description": "ModelJobs projects waiting steps from shared polling and queues reviewed decisions through JobSession.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected ModelJobs._observe, _observe_steps, _current_steps, _project_steps, _deciding, steps, read_steps, decision_outcome, decide, _finish_decision, actions, control (including WorkflowCancelUnavailable for a workflow cancel), _advancing and status, JobSession.decide_workflow_node, runtime.read_workflow_steps and decide_workflow_step, the local MCP workflow_job_steps and decide_workflow_step handlers and the review_step status descriptor. Installed tests on the packaged ZIP with synthetic SDK responses cover the projection after polling with no signed URL in status, the 15 second backoff, an immediate wait return, the status row, an approval sent once from another selected scene, a decision in flight counted as advancing, reject persisting canceled, ordered selections, blocked loop selections and stale review, revision, action, context and offline guards sending nothing, a refused decision reported without pausing, steps only after an explicit read following a restart, project-switch retirement, read_steps keeping an automatically polled job polled, reusing a refresh in flight and keeping a restarted job paused, each decision outcome, and a workflow cancel explained with no request. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No native review dialog exists yet; physical desktop evidence for the status row is pending. Re-reviewed on 2026-10-10 after the parser also blocked selections read by node types the API reference does not list, and again on 2026-10-10 for read_steps, decision_outcome, the workflow cancel explanation and the MCP tools that call them. Re-reviewed on 2026-10-10 after ModelJobs.control limited WorkflowCancelUnavailable to a running (remote) workflow job: a prepared, unsent workflow job keeps its cancel_prepared action and gets the ordinary refusal, as an installed test checks with no request; the cancellation sentence now says so. Re-reviewed on 2026-10-10 after _observe_steps began passing the coordinator's snapshot links to the parser. Installed tests with live-shaped job flows cover a selection into a loop without a readable definition offered only reject and its rejection sent, a definition proving the loop, a selection after a loop offered and sent with its definition read once, and an approval listing its definition review assets. Re-reviewed on 2026-10-12 after the parser's linear deduplication and full-dependency review asset count; this document's projection and decision statements are unchanged, including the decision error kept until another decision, a newly waiting step or the record leaving remote, which the installed refused-decision test asserts.",
    "sources": {
      "scenario/blender/model_jobs.py": "cb37cac5833fb7f5c96b2e4e23b41f75e11ba75f1dc75854b2db986733e3b7cf",
      "scenario/blender/job_session.py": "d82c0084fd2a8a34f1ee27d82366ed5ce6e1a526edc1312e817fdda93656d133",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/core/ui/saved_job_actions.py": "751b2d03f53d0439121dc4528f3fb8b1c683f9368a692b12b5c90cf50b51240e",
      "scenario/core/jobs/workflow_nodes.py": "66318468f9afbe9cadeb46faef90baabbded456def4a339bc214073d4e29c720",
      "tests/blender/test_workflow_commands.py": "ef1a5fe27ed2cfceff78f876a76c7fad00b1a35f1f22d6c9d85e34005ef06e09",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a",
      "scenario/mcp/tools_scenario.py": "773411b23643e7e1610476625ad5ffbfe0ee4a4ba63fa57500d99cb2467bec0d",
      "scenario/core/jobs/coordinator.py": "4c7a7242c8f295650cd548bddd1db0bfe197da487998f2897de03a78830a4882"
    }
  }
}
---

# Waiting workflow steps in the shared session

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
