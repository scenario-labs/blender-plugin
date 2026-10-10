---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.waiting-workflow-steps",
  "title": "Waiting workflow steps in the runtime map",
  "description": "Shared polling projects waiting workflow steps and one decision path serves UI and MCP.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the Active workflow commands paragraph matches the shared projection in ModelJobs, the coordinator decision command and runtime.decide_workflow_step, that rejection is the only workflow cancellation and that cancel_remote stays model-only. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Native and MCP decision controls and running-step cancellation remain absent.",
    "sources": {
      "scenario/blender/model_jobs.py": "14737547ccaf27acb7efed4a937314f8808b54afa52ef7b8e21e2c0d9e0f4d24",
      "scenario/blender/runtime.py": "37a9c2428e3f4c5befb9226f2f923f93202cc336fd49eb77a1368f8551c27c1c",
      "scenario/core/jobs/coordinator.py": "748c445070b9c3430a6ee28c9dbed94e2463b6703e076c83200cfdb36e843cfa",
      "scenario/core/jobs/workflow_nodes.py": "94a38896e6331e6dc993a5a83ecdb7b740ab5f60897bab73e7f45f4dbcade4d2",
      "tests/blender/test_workflow_commands.py": "c801ddf916034704b16fe25384ef9ee319b3c1c81f4ec4ede5577b2f7ce84776",
      "tests/unit/test_workflow_decisions.py": "9022e540c17121895aa93826922ac59e3e4ddfe508701931896e2f86e98eeeda"
    }
  }
}
---

# Waiting workflow steps in the runtime map

Evidence for [the canonical document](../../architecture/runtime.md).
