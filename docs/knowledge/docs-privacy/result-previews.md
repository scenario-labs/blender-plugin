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
    "limits": "Inspected the cache location, stored fields including still dimensions, eviction that counts only bytes actually removed, recreation of a deleted root by the next lane command, and the content transfers used for server preview images and clips. No user-facing control schedules previews yet; this does not establish live CDN hosts or data retention.",
    "sources": {
      "scenario/blender/runtime.py": "aa199b156270fbc86aa6dbc5edf30096dddac7e69de6cc1ea905d5619b2a51bb",
      "scenario/core/jobs/result_previews.py": "98251f4403a649291869c94cf7893384476382074b41b68b5778043809bb8aa1",
      "scenario/core/jobs/preview_scheduler.py": "cb75fc5ff870438352430c331ea7a2a4a5d9da307dfb44ad9a44bfbdb2c5e7dc",
      "tests/unit/test_result_previews.py": "ffa3b2587cb45331d2bec3c6a21a194e661c2adac17b860cf9804fb777dc60a7"
    }
  }
}
---

# Saved-result preview cache and transfers

Evidence for [the canonical document](../../PRIVACY.md).
