---
{
  "type": "Evidence",
  "id": "docs-privacy.result-previews",
  "title": "Saved-result preview cache and transfers",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the cache location, stored fields including still dimensions, eviction that counts only bytes actually removed and also runs as a maintenance-only lane pass after writes once no preview batch is due, recreation of a deleted root by the next lane command, and the content transfers used for server preview images and clips. No user-facing control schedules previews yet; this does not establish live CDN hosts or data retention.",
    "sources": {
      "scenario/blender/runtime.py": "aa199b156270fbc86aa6dbc5edf30096dddac7e69de6cc1ea905d5619b2a51bb",
      "scenario/core/jobs/result_previews.py": "d33234f02a85f67a573ca1d097ebd8921578ba3c38047811249ac4484367c7d3",
      "scenario/core/jobs/preview_scheduler.py": "bfe2b96bad5f175a28ca71b95d6cc0d478e40ee009e55c7929724fca88898a65",
      "tests/unit/test_result_previews.py": "937a378d1aa27ff7e9aa1ff2f086521bd62fd52d26227297029febe3d75a1fbd",
      "tests/unit/test_preview_scheduler.py": "3dc08f8f31f906e3926a84ee1eaa7ad99cf146ba7ebbcae0e1941c8af89f58e8"
    }
  }
}
---

# Saved-result preview cache and transfers

Evidence for [the canonical document](../../PRIVACY.md).
