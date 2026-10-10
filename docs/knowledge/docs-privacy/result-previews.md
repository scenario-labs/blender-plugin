---
{
  "type": "Evidence",
  "id": "docs-privacy.result-previews",
  "title": "Saved-result preview cache and transfers",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the cache location, stored fields including still dimensions, eviction that counts only bytes actually removed and also runs as a maintenance-only lane pass after writes once no preview batch is due, recreation of a deleted root by the next lane command, and the content transfers used for server preview images and clips. Only Load previews on a waiting workflow step schedules previews; this does not establish live CDN hosts or data retention. Re-reviewed on 2026-10-10: the cache paragraph adds the stills of a waiting workflow step's review assets (the images up to 8 MiB each, or their server thumbnails) whose icons stay in memory and never enter Blender's file-thumbnail cache, and the content URL list adds workflow review images; checked against review_sources, check_still and review_previews.py, added as a source with the review preview tests. Only the fingerprints of touched sources that matched the base were refreshed.",
    "sources": {
      "scenario/blender/runtime.py": "56d4afe7ddb394b23d735c1f7b9e981c4a032963323ac50473f26b09ba9bd6ef",
      "scenario/core/jobs/result_previews.py": "b17c9f0ebd80e222090c0ad83339b27d7f261a7e1cb5a7bf02d2ca261d9ceb09",
      "scenario/core/jobs/preview_scheduler.py": "aedd1fa55614dd342688a15bba9639fb31f10590d2bbd7dfd4be2344912641d2",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46",
      "tests/unit/test_preview_scheduler.py": "42f7b5057fd0ef01e788a60e9201d7aad8e8e5a75e0d7b3174e11e3ed9b605dd",
      "scenario/blender/review_previews.py": "508f3a424412cc7b95a9d78870b9c765d3b8c3ee2eeb44ddc010cd193d451bba",
      "tests/unit/test_workflow_review_previews.py": "12fb0b5f4f8cd6f15c5868996ef108f01192fadf4e9f70f1b62f1b0c6a38a83e",
      "tests/blender/test_workflow_review_previews.py": "4f8100b75a020836378862af5375d04f86b21cf37ba2220553c3525767157452"
    }
  }
}
---

# Saved-result preview cache and transfers

Evidence for [the canonical document](../../PRIVACY.md).
