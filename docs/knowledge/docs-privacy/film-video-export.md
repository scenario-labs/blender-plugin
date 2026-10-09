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
    "limits": "Inspected the export destination, private staging contents, the single local log line with basename and SHA-256, and crash leftovers next to the destination. No network activity is involved; no legal-policy audit. Re-reviewed after the hidden partial file moved to a fixed .scenario-<hex>.partial name and destinations inside staging, extension or Blender user storage became refused; the privacy wording remains accurate. Re-reviewed after the placeholder pin, free-space checks and private-root folding; no new file or log content, and the wording remains accurate.",
    "sources": {
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "ef8b3ccafefa6e0f101dedc462732ee2be7d33489aa86b72876418c308eaabf3"
    }
  }
}
---

Source evidence for [the canonical guide](../../PRIVACY.md).
