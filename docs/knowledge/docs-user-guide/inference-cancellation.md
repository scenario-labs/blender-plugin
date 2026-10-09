---
{
  "type": "Evidence",
  "id": "docs-user-guide.inference-cancellation",
  "title": "Inference-only Cancel generation",
  "description": "When the Jobs panel offers Cancel generation for a running job.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "inference-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Jobs panel controls: job_recovery.draw_controls draws Cancel generation only when ModelJobs.actions lists cancel, which requires a remote model job whose latest refresh in this session reported jobType inference. After a restart the recovered job is paused and offers Refresh status; cancellation appears only after that explicit refresh. Other running jobs show no cancel button, keep polling and remain recoverable from saved jobs. Installed tests cover the native operator refusing a custom job without a request. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims through the packaged extension with a mock transport. Only the public job action reference (https://docs.scenario.com/api/resources/jobs/methods/trigger_action) and the pinned SDK 2.2.0 jobs.trigger_action docstring, both reading 'Today only cancel on inference jobs is supported', establish eligibility; no live service cancellation, no live check of which lanes return inference jobs and no desktop interaction or screenshot is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/job_recovery.py": "1e85d4bb6ab63c6a72a8911c5f99a5a4448a94596ef673f8692fc7b2d3c5e35c",
      "scenario/blender/model_jobs.py": "f87c0f601a18328379fb6049209fd9c0d84fb04892ae0c3f1d93ecece3b51fbe",
      "tests/blender/test_model_generation.py": "a7fab51a6b06a620be36fc239cc8b97fab1a4e455e0fc770ed9f2e831ffe0867"
    }
  }
}
---

# Inference-only Cancel generation

Evidence for [the canonical document](../../USER_GUIDE.md).
