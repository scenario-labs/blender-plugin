---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.inference-cancellation",
  "title": "Inference-only cancellation offer",
  "description": "Shared saved-job control offering remote cancellation only for observed inference jobs.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "inference-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ModelJobs: poll passes each successful refresh_remote or cancel_remote RemoteSnapshot to _observe_cancellation, which records the remote ID only for a remote record whose response repeats that ID and reports a cancellable_job type, and withdraws it otherwise; the view loop drops it once the record leaves remote. actions() lists cancel only for a remote model record with that in-memory observation, so the native Jobs panel (job_recovery.draw_controls) and MCP job_status show the same list. control() answers a cancel for an unconfirmed remote model record with CANCEL_UNSUPPORTED before any command, and a coordinator CancellationUnsupported completion withdraws the offer and pauses delivery with the same message without a claim. Installed tests cover a custom job with no offer and refusal through MCP recover_local_job and the native recover_job operator with no POST and an unchanged record, an inference job canceled once, no offer after restart until an explicit refresh, a changed job type refused before the claim, and session-level refusal with a single GET. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims through the packaged extension with a mock transport. Only the public job action reference (https://docs.scenario.com/api/resources/jobs/methods/trigger_action) and the pinned SDK 2.2.0 jobs.trigger_action docstring, both reading 'Today only cancel on inference jobs is supported', establish eligibility; no live service cancellation, no live check of which lanes return inference jobs and no desktop interaction or screenshot is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/model_jobs.py": "f87c0f601a18328379fb6049209fd9c0d84fb04892ae0c3f1d93ecece3b51fbe",
      "scenario/blender/job_recovery.py": "1e85d4bb6ab63c6a72a8911c5f99a5a4448a94596ef673f8692fc7b2d3c5e35c",
      "scenario/blender/runtime.py": "fb83ceaa622cbbfbea25210d2bb8d480231510d11712f58df34f45f41c13cf59",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "scenario/core/jobs/coordinator.py": "90762a0037ef21524495fdfd6fbae77b40171f59b2533ed043d4f0674901cb7b",
      "scenario/mcp/tools_scenario.py": "a67d946947981ba07a4acb4ae6ffb8e87e955f2af934d2e94d1ad50f1cd403fd",
      "tests/blender/test_model_generation.py": "a7fab51a6b06a620be36fc239cc8b97fab1a4e455e0fc770ed9f2e831ffe0867",
      "tests/blender/test_job_session.py": "7ae4a36b3377ae74605f3cbd2826f64c43c4aa76eb74bc49fae7cfde69e9097f"
    }
  }
}
---

# Inference-only cancellation offer

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
