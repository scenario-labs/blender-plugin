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
    "limits": "Inspected the cache location, stored fields including still dimensions, eviction that counts only bytes actually removed and also runs as a maintenance-only lane pass after writes once no preview batch is due, recreation of a deleted root by the next lane command, and the content transfers used for server preview images and clips. No user-facing control schedules previews yet; this does not establish live CDN hosts or data retention.",
    "sources": {
      "scenario/blender/runtime.py": "56d4afe7ddb394b23d735c1f7b9e981c4a032963323ac50473f26b09ba9bd6ef",
      "scenario/core/jobs/result_previews.py": "d33234f02a85f67a573ca1d097ebd8921578ba3c38047811249ac4484367c7d3",
      "scenario/core/jobs/preview_scheduler.py": "5ab4cf0b258aff1217223dcc8c4bbef4e09e664594c6e61cdf3156115b71a53c",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46",
      "tests/unit/test_preview_scheduler.py": "42f7b5057fd0ef01e788a60e9201d7aad8e8e5a75e0d7b3174e11e3ed9b605dd"
    }
  }
}
---

# Saved-result preview cache and transfers

Evidence for [the canonical document](../../PRIVACY.md).
