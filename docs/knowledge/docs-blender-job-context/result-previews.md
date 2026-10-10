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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected JobSession preview configuration, main-thread access, maintenance-timer servicing, deactivation, the idle-lane condition for reaping retired sessions and shutdown cleanup, and the runtime cache root. Native installed-ZIP tests on Blender 5.1.2 macOS arm64 cover lane threads, unchanged bpy data and job records, a retired session that stays registered without blocking while a preview read ignores cancellation, the 0700 runtime cache root, a cache root that cannot be created and leaves jobs available without previews, and unconfigured sessions. Hosted baseline CI also runs tests/blender/test_result_previews.py on Linux and Windows with Blender 5.0.1, 5.1.2 and 5.2.1. tests/blender/test_runtime_jobs.py, which holds the runtime cache-root cases, is outside that baseline and ran natively only on 5.1.2 macOS arm64, so those cases are unverified on other versions and platforms. GUI timers in a desktop session, extension disable during preview I/O and any user-facing preview are unverified.",
    "sources": {
      "scenario/blender/job_session.py": "a47e759441bddfd645e1dd17626600dc3c81d1e0938488619d31c69f11f804d2",
      "scenario/blender/runtime.py": "aa199b156270fbc86aa6dbc5edf30096dddac7e69de6cc1ea905d5619b2a51bb",
      "scenario/core/jobs/preview_scheduler.py": "cb75fc5ff870438352430c331ea7a2a4a5d9da307dfb44ad9a44bfbdb2c5e7dc",
      "tests/blender/test_result_previews.py": "a42261da4a269ef3e91b76f2260eca6d81d17831d51f29fb2c1cb62972e8b2e2",
      "tests/blender/test_runtime_jobs.py": "56f200b664856a6ac44820ae48f605fc48b59a745733e70cf09d6e89278d29f4",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f"
    }
  }
}
---

# Saved-result preview ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
