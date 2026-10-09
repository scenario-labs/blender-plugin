---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.result-previews",
  "title": "Saved-result preview ownership",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected JobSession preview configuration, main-thread access, maintenance-timer servicing, deactivation and shutdown cleanup, and the runtime cache root. Native installed-ZIP tests on Blender 5.1.2 macOS arm64 cover lane threads, unchanged bpy data and job records, retirement and unconfigured sessions. Blender 5.0 and 5.2, other platforms, GUI timers in a desktop session and any user-facing preview are unverified.",
    "sources": {
      "scenario/blender/job_session.py": "a4a5a108a4b500ce09448f027243973a6116f8e615bcc7444902a561741a772d",
      "scenario/blender/runtime.py": "5c7d192dcdc8cbfc0b3e3d13d4e786d8bbaee67b855d6deaad80eaf0b08d746d",
      "scenario/core/jobs/preview_scheduler.py": "4a8d4924e4e959be28ab314ddce976f5e7290cf461ae8e784475e185da0d28f7",
      "tests/blender/test_result_previews.py": "bcb6a24461461201d7f3560f87c261f433cb3adf30d111936d815d917be9b7de",
      "tests/blender/test_runtime_jobs.py": "27bcbb1be51e08e0e6558d44a69f0bc79887b0035324242e19affe151f0b65c4"
    }
  }
}
---

# Saved-result preview ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
