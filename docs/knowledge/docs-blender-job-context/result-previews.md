---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.result-previews",
  "title": "Saved-result preview ownership",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected JobSession preview configuration, main-thread access, maintenance-timer servicing, which can also queue the scheduler's cache maintenance, deactivation, the idle-lane condition for reaping retired sessions and shutdown cleanup, and the runtime cache root. Native installed-ZIP tests on Blender 5.1.2 macOS arm64 cover lane threads, unchanged bpy data and job records, a retired session that stays registered without blocking while a preview read ignores cancellation, the 0700 runtime cache root, a cache root that cannot be created and leaves jobs available without previews, and unconfigured sessions. Hosted baseline CI also runs tests/blender/test_result_previews.py on Linux and Windows with Blender 5.0.1, 5.1.2 and 5.2.1. tests/blender/test_runtime_jobs.py, which holds the runtime cache-root cases, is outside that baseline and ran natively only on 5.1.2 macOS arm64, so those cases are unverified on other versions and platforms. GUI timers in a desktop session, extension disable during preview I/O and any user-facing preview are unverified. Re-reviewed on 2026-10-10: the preview ownership paragraph adds review assets keyed by the saved workflow job through request_review, runtime.load_review_previews binding the request to the context, saved revision and review_id, and the runtime-owned review previews object cleared when jobs retire; checked against those and the installed review preview tests, added as sources with review_previews.py. Only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 after two review preview fixes: the preview ownership paragraph adds that the review previews decode in temporary Blender data, never by loading and removing a bpy.data image, so the dependency handler sees no update and origins captured in the scene stay current; checked against review_previews.py, preview_decode.py, added as a source, JobSession's dependency handler and the installed test that captures an origin before a decode. Only the touched fingerprints were refreshed.",
    "sources": {
      "scenario/blender/job_session.py": "856baab7ec8aa2786f27ee482b0acc30a8f895fe547664e905b43304ad0ed08a",
      "scenario/blender/runtime.py": "56d4afe7ddb394b23d735c1f7b9e981c4a032963323ac50473f26b09ba9bd6ef",
      "scenario/core/jobs/preview_scheduler.py": "aedd1fa55614dd342688a15bba9639fb31f10590d2bbd7dfd4be2344912641d2",
      "tests/blender/test_result_previews.py": "a42261da4a269ef3e91b76f2260eca6d81d17831d51f29fb2c1cb62972e8b2e2",
      "tests/blender/test_runtime_jobs.py": "56f200b664856a6ac44820ae48f605fc48b59a745733e70cf09d6e89278d29f4",
      "scenario/core/jobs/workers.py": "dece4686af0b0889b99341a99d6d5143d48cdf63919fecef90299b834fbe9bc3",
      "scenario/blender/review_previews.py": "65a68e371515d154f6be66e4fc49bbfe9bb075bbeebdeb987db83a40abd9f504",
      "tests/blender/test_workflow_review_previews.py": "d4c46ed53bf965383091a63da3f94caa41036b8dad377296bd2dd406e3ab7a67",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Saved-result preview ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
