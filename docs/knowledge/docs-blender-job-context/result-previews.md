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
    "base_revision": "ad143c8e2406123217888301badcb49638033fd8",
    "limits": "Inspected JobSession preview configuration, main-thread access, maintenance-timer servicing, deactivation, the idle-lane condition for reaping retired sessions and shutdown cleanup, and the runtime cache root. Native installed-ZIP tests on Blender 5.1.2 macOS arm64 cover lane threads, unchanged bpy data and job records, a retired session that stays registered without blocking while a preview read ignores cancellation, the 0700 runtime cache root and unconfigured sessions. Blender 5.0 and 5.2, other platforms, GUI timers in a desktop session, extension disable during preview I/O and any user-facing preview are unverified.",
    "sources": {
      "scenario/blender/job_session.py": "f8ea693820df79a9e51d103873349f0e5d6512996841f0536dd091b15438757c",
      "scenario/blender/runtime.py": "5c7d192dcdc8cbfc0b3e3d13d4e786d8bbaee67b855d6deaad80eaf0b08d746d",
      "scenario/core/jobs/preview_scheduler.py": "f9e20eaa003f7baafee3d8ddb78730b459741b2330bc8a21e9b6dff140efdc03",
      "tests/blender/test_result_previews.py": "ae1ee17104e5f7efa18e3eb36b8b75bc9606f21a9c7b3c1be44f2a494680cebd",
      "tests/blender/test_runtime_jobs.py": "b91eb341688bcd0be34dfa5a104a3a99a18ff13e8748ffbbeab56fe059306fdc",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f"
    }
  }
}
---

# Saved-result preview ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
