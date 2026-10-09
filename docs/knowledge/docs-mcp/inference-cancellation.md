---
{
  "type": "Evidence",
  "id": "docs-mcp.inference-cancellation",
  "title": "Inference-only recover_local_job cancel",
  "description": "MCP cancellation parity with the native Jobs panel.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "inference-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed recover_local_job, which calls runtime.control_model_job and therefore ModelJobs.control, and job_status, whose actions come from ModelJobs.actions. cancel is listed only after a refresh in the current owner reported a remote inference job; any other cancel for a remote model job raises the shared CANCEL_UNSUPPORTED ScenarioError without a request, and the job keeps polling. The recover_local_job description states this; the generated tool table carries only its unchanged first line, and tools/gen_mcp_docs.py --check passes. Installed tests exercise MCP refusal for a custom job, cancel after an inference refresh, refusal after restart until refresh and a changed type refused before the claim. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims through the packaged extension with a mock transport. Only the public job action reference (https://docs.scenario.com/api/resources/jobs/methods/trigger_action) and the pinned SDK 2.2.0 jobs.trigger_action docstring, both reading 'Today only cancel on inference jobs is supported', establish eligibility; no live service cancellation, no live check of which lanes return inference jobs and no desktop interaction or screenshot is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "a67d946947981ba07a4acb4ae6ffb8e87e955f2af934d2e94d1ad50f1cd403fd",
      "scenario/blender/model_jobs.py": "f87c0f601a18328379fb6049209fd9c0d84fb04892ae0c3f1d93ecece3b51fbe",
      "scenario/blender/runtime.py": "fb83ceaa622cbbfbea25210d2bb8d480231510d11712f58df34f45f41c13cf59",
      "tests/blender/test_model_generation.py": "a7fab51a6b06a620be36fc239cc8b97fab1a4e455e0fc770ed9f2e831ffe0867",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e"
    }
  }
}
---

# Inference-only recover_local_job cancel

Evidence for [the canonical document](../../MCP.md).
