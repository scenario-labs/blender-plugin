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
    "limits": "Inspected the cache location, stored fields, eviction and deletion safety, and the content transfers used for server preview images and clips. No user-facing control schedules previews yet; this does not establish live CDN hosts or data retention.",
    "sources": {
      "scenario/blender/runtime.py": "5c7d192dcdc8cbfc0b3e3d13d4e786d8bbaee67b855d6deaad80eaf0b08d746d",
      "scenario/core/jobs/result_previews.py": "c8c8574a201ddbd979126120c0ae872ecaff851a00661b2a12472991a55b9cce",
      "scenario/core/jobs/preview_scheduler.py": "4a8d4924e4e959be28ab314ddce976f5e7290cf461ae8e784475e185da0d28f7",
      "tests/unit/test_result_previews.py": "ee00b4a254224b007ce89d6fca50fdf6806ba0381847fe93ee4bcd0b5563aa6c"
    }
  }
}
---

# Saved-result preview cache and transfers

Evidence for [the canonical document](../../PRIVACY.md).
