---
{
  "type": "Evidence",
  "id": "docs-user-guide.prepared-job-cancellation",
  "title": "Cancel prepared job in the Jobs panel",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "prepared-job-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the Cancel prepared job saved-job control for unsent prepared model and workflow jobs, including queued or restarted ones. It asks for confirmation, then cancels locally through the same command as MCP cancel_prepared_job without a service request; claimed, stale or changed-context jobs are rejected. Installed native tests on macOS arm64 Blender 5.1.2 cover these paths with mocked transports. Prompt and translate jobs do not show this control. No desktop dialog interaction, screenshot, other Blender version or OS, or live acceptance is claimed. Other guide topics retain their own evidence.",
    "sources": {
      "scenario/blender/job_recovery.py": "b5cfc9abef6ea4324616158292a84164e3211851463d8e58371e875dd0d7a796",
      "scenario/blender/model_jobs.py": "2c3e5ae36c87ef8be8194c2f5502c4f2ddb63f574a46c7823bf546292f551633",
      "scenario/blender/runtime.py": "3f7a1467c516c11642bc81dfba323efa972fc5a6305e26f0d3f324dad3844981",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "tests/blender/test_runtime_jobs.py": "51463a0b7bb672ea0fcc15189f4bf2de269eaaff8aac94f52fa59a4d82802a03",
      "tests/blender/test_model_generation.py": "05a97189a433b036e7cae5dc41ddbbe40374f4fa632eecec0e341819914e3a62"
    }
  }
}
---

# Cancel prepared job in the Jobs panel

Evidence for [the canonical guide](../../USER_GUIDE.md).
