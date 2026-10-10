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
    "limits": "Inspected ModelJobs._observe, _observe_steps, _current_steps, _project_steps, _deciding, steps, step_view, waiting_step, read_steps, decision_outcome, decide, _finish_decision, actions, control (including WorkflowCancelUnavailable for a running workflow cancel), _advancing and status, JobSession.decide_workflow_node, runtime.read_workflow_steps and decide_workflow_step, the local MCP workflow_job_steps and decide_workflow_step handlers, job_recovery.result_actions and workflow_steps, saved_job_actions.describe and the native review dialog in workflow_steps. This topic also covers the Active saved-job controls sentences on descriptor properties and on the step projection that descriptors read. Installed tests on the packaged ZIP with synthetic SDK responses cover the projection after polling with no signed URL in status, the 15 second backoff, an immediate wait return, an approval sent once from another selected scene, a decision in flight counted as advancing, reject persisting canceled, ordered selections, blocked loop selections and stale review, revision, action, context and offline guards sending nothing, a refused decision reported without pausing, steps only after an explicit read following a restart, project-switch retirement, read_steps behavior, each decision outcome, a workflow cancel explained with no request, and the native dialog's capture, single use and rechecks through the same entry. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Re-reviewed on 2026-10-10 after the review dialog's decision cells became an even split and its minimum width 540; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10: the Native review of waiting steps subsection adds ModelJobs.review_assets (the step's review asset IDs with the decision binding, without refusing a command in flight) and that Load previews passes them to the review previews; checked against model_jobs.py, workflow_nodes.preview_assets and the installed review preview tests, added as a source. The decision claims are unchanged; only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 after two review preview fixes: the installed review preview tests gained origin and retry cases; the review_assets binding and the Load previews hand-off described here are unchanged, and only that test file's fingerprint was refreshed. Re-reviewed on 2026-10-10 after _observe_steps began passing the coordinator's snapshot links to the parser. Installed tests with live-shaped job flows cover a selection into a loop without a readable definition offered only reject and its rejection sent, a definition proving the loop, a selection after a loop offered and sent with its definition read once, and an approval listing its definition review assets. Re-reviewed on 2026-10-12 after the parser's linear deduplication and full-dependency review asset count; this document's projection and decision statements are unchanged, including the decision error kept until another decision, a newly waiting step or the record leaving remote, which the installed refused-decision test asserts.",
    "sources": {
      "scenario/blender/model_jobs.py": "a495102b2780ac37e4260493cea3cfbd8bd0c7130fde4954ae301e511ab701e0",
      "scenario/blender/job_session.py": "d82c0084fd2a8a34f1ee27d82366ed5ce6e1a526edc1312e817fdda93656d133",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/blender/job_recovery.py": "425f54316c84067f910f15a1873a7d5175a372e4cf357bca517966cdcc6a5d8e",
      "scenario/blender/workflow_steps.py": "e48ff16971de14b0d350a304a7475af19bf428df642dd199cd72181a2042222c",
      "scenario/core/ui/saved_job_actions.py": "b22a28c37971c21776313bdef903af8ee9d24e627774ffd4d14c48ef59e8ab4b",
      "scenario/core/jobs/workflow_nodes.py": "817af2ea9ee2777797150c1f6f3ccbadf7ee9dbcfe6ca2da289233cd1e9793f2",
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/blender/test_workflow_steps.py": "77cdf3ee05fc38f0a99de909b751a50bb6188af72938a339efa0b9bf27baf189",
      "tests/unit/test_saved_job_actions.py": "ac7679b2665509d333855b3c7f26bed297c856a26391a200aa800444f9f16379",
      "tests/blender/test_workflow_review_previews.py": "d4c46ed53bf965383091a63da3f94caa41036b8dad377296bd2dd406e3ab7a67",
      "scenario/core/jobs/coordinator.py": "4c7a7242c8f295650cd548bddd1db0bfe197da487998f2897de03a78830a4882"
    }
  }
}
---

# Waiting workflow steps in the shared session

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
