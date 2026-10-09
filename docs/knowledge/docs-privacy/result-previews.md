---
{
  "type": "Evidence",
  "id": "docs-privacy.result-previews",
  "title": "Saved-result preview cache and transfers",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the cache location, stored fields including still dimensions, eviction, recreation of a deleted root by the next lane command, and the content transfers used for server preview images and clips. No user-facing control schedules previews yet; this does not establish live CDN hosts or data retention.",
    "sources": {
      "scenario/blender/runtime.py": "e7d96070a984d22c589b33c035597fec6f3b2eb53ae28551c3e26b82f6b5ee34",
      "scenario/core/jobs/result_previews.py": "fccebeef052749a0e98678df789f35660ebdbc37eb30b79f978e5ef68b714701",
      "scenario/core/jobs/preview_scheduler.py": "ba072b0748b5210527ed953da66794a8e3fca3617608960bc8a0a57a42d9737c",
      "tests/unit/test_result_previews.py": "3b1ef379ff47c48ef181da224c22db1cf1eaed3ffe4d5a161461a7ad066c4eb4"
    }
  }
}
---

# Saved-result preview cache and transfers

Evidence for [the canonical document](../../PRIVACY.md).
