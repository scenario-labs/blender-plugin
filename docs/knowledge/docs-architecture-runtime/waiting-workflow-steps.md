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
    "limits": "Reviewed that the Active workflow commands paragraph matches the shared projection in ModelJobs, the coordinator decision command and runtime.decide_workflow_step, that rejection is the only workflow cancellation and that cancel_remote stays model-only. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Native and MCP decision controls and running-step cancellation remain absent. Re-reviewed on 2026-10-10 after the parser also blocked selections read by node types the API reference does not list; the runtime map paragraph is unchanged by it. Re-reviewed on 2026-10-10 after the projection began reading step links from the workflow definition; the runtime map paragraph remains accurate and is unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "b52d70361f3e6cdd50fb8cc236e2da5aaa9be003252e859f1ba24d3cc7e80798",
      "scenario/blender/runtime.py": "37a9c2428e3f4c5befb9226f2f923f93202cc336fd49eb77a1368f8551c27c1c",
      "scenario/core/jobs/coordinator.py": "4c7a7242c8f295650cd548bddd1db0bfe197da487998f2897de03a78830a4882",
      "scenario/core/jobs/workflow_nodes.py": "81a15c7f5bc51c74dd94d8abe1f5e1d44d9db12fdea35d79fb2c967f3e65f261",
      "tests/blender/test_workflow_commands.py": "e470e6a96fbeda7eab66a6d9fe71c00aa224c7361f833684f76fc94fc5be8282",
      "tests/unit/test_workflow_decisions.py": "bed926329df85c217701d8bc0141d5645d98cf5d32ee9372de4644404a9cac2d"
    }
  }
}
---

# Waiting workflow steps in the runtime map

Evidence for [the canonical document](../../architecture/runtime.md).
