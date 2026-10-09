---
{
  "type": "Evidence",
  "id": "docs-privacy.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the export destination, private staging contents, the single local log line with basename and SHA-256, and crash leftovers next to the destination. No network activity is involved; no legal-policy audit.",
    "sources": {
      "scenario/blender/local_capture.py": "79391e7f3eb1f59c07bc948ec267841ce4ef682159437aae64b9b03b21fc6dd7",
      "scenario/core/jobs/coordinator.py": "08cfc053a4b27cac03e4002dab7429de06516ccdfeec9d1243a84e3414e7ba1d",
      "scenario/core/jobs/local_export.py": "ca449fe8eb3969af94534488bfadd3789c98985205dc421225431398c4a81164"
    }
  }
}
---

Source evidence for [the canonical guide](../../PRIVACY.md).
