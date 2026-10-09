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
    "limits": "Inspected JobSession preview configuration, main-thread access, maintenance-timer servicing, deactivation, the idle-lane condition for reaping retired sessions and shutdown cleanup, and the runtime cache root. Native installed-ZIP tests on Blender 5.1.2 macOS arm64 cover lane threads, unchanged bpy data and job records, a retired session that stays registered without blocking while a preview read ignores cancellation, the 0700 runtime cache root, a cache root that cannot be created and leaves jobs available without previews, and unconfigured sessions. Blender 5.0 and 5.2, other platforms, GUI timers in a desktop session, extension disable during preview I/O and any user-facing preview are unverified.",
    "sources": {
      "scenario/blender/job_session.py": "f8ea693820df79a9e51d103873349f0e5d6512996841f0536dd091b15438757c",
      "scenario/blender/runtime.py": "e7d96070a984d22c589b33c035597fec6f3b2eb53ae28551c3e26b82f6b5ee34",
      "scenario/core/jobs/preview_scheduler.py": "ba072b0748b5210527ed953da66794a8e3fca3617608960bc8a0a57a42d9737c",
      "tests/blender/test_result_previews.py": "a42261da4a269ef3e91b76f2260eca6d81d17831d51f29fb2c1cb62972e8b2e2",
      "tests/blender/test_runtime_jobs.py": "dc7ad681a477b8f926e35eabde60b9d76f18e86ac97b901473f81abea58582a6",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f"
    }
  }
}
---

# Saved-result preview ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
