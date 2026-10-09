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
    "limits": "Inspected the export destination, private staging contents, the single local log line with basename and SHA-256, and crash leftovers next to the destination. No network activity is involved; no legal-policy audit. Re-reviewed after the hidden partial file moved to a fixed .scenario-<hex>.partial name and destinations inside staging, extension or Blender user storage became refused; the privacy wording remains accurate.",
    "sources": {
      "scenario/blender/local_capture.py": "0273dc52526b0805491eef982cc37708a4f80e8d2518f48de43d1babde52b2a2",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "244d39066b8da9af7fd365e04313b54de46732bafbb0167a82111b4d142d4f79"
    }
  }
}
---

Source evidence for [the canonical guide](../../PRIVACY.md).
