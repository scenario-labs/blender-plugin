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
      "scenario/blender/runtime.py": "7ba1a04feddcf53987879cd57406210f2aa9fe7aa7e2c3a1e9fcbd54714eef46",
      "scenario/core/jobs/result_previews.py": "afd49b8052fd0953c1b1fe10b8a8f3f6fd6e383a7d5ddd6647aa4f00e002d893",
      "scenario/core/jobs/preview_scheduler.py": "f9e20eaa003f7baafee3d8ddb78730b459741b2330bc8a21e9b6dff140efdc03",
      "tests/unit/test_result_previews.py": "d34505132b8d4474911889ac697e848d3653593fa34ddb0eac3fb62794e9f830"
    }
  }
}
---

# Saved-result preview cache and transfers

Evidence for [the canonical document](../../PRIVACY.md).
