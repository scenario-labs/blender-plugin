---
{
  "type": "Evidence",
  "id": "docs-user-guide.waiting-workflow-steps",
  "title": "Waiting workflow steps in Jobs",
  "description": "A waiting workflow shows a status row; deciding from Blender is not available yet.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the review_step status descriptor, its Jobs drawing through job_recovery.draw_controls and the 15 second refresh while a step waits. Installed tests check the descriptor label on a projected view; no screenshot or physical desktop interaction was captured. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "751b2d03f53d0439121dc4528f3fb8b1c683f9368a692b12b5c90cf50b51240e",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/model_jobs.py": "14737547ccaf27acb7efed4a937314f8808b54afa52ef7b8e21e2c0d9e0f4d24",
      "tests/blender/test_workflow_commands.py": "c801ddf916034704b16fe25384ef9ee319b3c1c81f4ec4ede5577b2f7ce84776",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a"
    }
  }
}
---

# Waiting workflow steps in Jobs

Evidence for [the canonical document](../../USER_GUIDE.md).
