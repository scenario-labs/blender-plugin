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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected ModelJobs._observe, _observe_steps, _current_steps, _project_steps, _deciding, steps, decide, _finish_decision, actions, control, _advancing and status, JobSession.decide_workflow_node, runtime.decide_workflow_step and the review_step status descriptor. Installed tests on the packaged ZIP with synthetic SDK responses cover the projection after polling with no signed URL in status, the 15 second backoff, an immediate wait return, the status row, an approval sent once from another selected scene, a decision in flight counted as advancing, reject persisting canceled, ordered selections, blocked loop selections and stale review, revision, action, context and offline guards sending nothing, a refused decision reported without pausing, steps only after an explicit refresh following a restart, and project-switch retirement. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No native review dialog or MCP decision tool exists yet; physical desktop evidence for the status row is pending.",
    "sources": {
      "scenario/blender/model_jobs.py": "14737547ccaf27acb7efed4a937314f8808b54afa52ef7b8e21e2c0d9e0f4d24",
      "scenario/blender/job_session.py": "d82c0084fd2a8a34f1ee27d82366ed5ce6e1a526edc1312e817fdda93656d133",
      "scenario/blender/runtime.py": "37a9c2428e3f4c5befb9226f2f923f93202cc336fd49eb77a1368f8551c27c1c",
      "scenario/core/ui/saved_job_actions.py": "751b2d03f53d0439121dc4528f3fb8b1c683f9368a692b12b5c90cf50b51240e",
      "scenario/core/jobs/workflow_nodes.py": "94a38896e6331e6dc993a5a83ecdb7b740ab5f60897bab73e7f45f4dbcade4d2",
      "tests/blender/test_workflow_commands.py": "c801ddf916034704b16fe25384ef9ee319b3c1c81f4ec4ede5577b2f7ce84776",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a"
    }
  }
}
---

# Waiting workflow steps in the shared session

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
