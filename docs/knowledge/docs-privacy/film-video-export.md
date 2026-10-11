---
{
  "type": "Evidence",
  "id": "docs-privacy.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the export destination, private staging contents, the single local log line with basename and SHA-256, and crash leftovers next to the destination. No network activity is involved; no legal-policy audit. Re-reviewed after the hidden partial file moved to a fixed .scenario-<hex>.partial name and destinations inside staging, extension or Blender user storage became refused; the privacy wording remains accurate. Re-reviewed after the placeholder pin, free-space checks and private-root folding; no new file or log content, and the wording remains accurate. Re-reviewed after the rebase onto 72723f02, whose coordinator changes retire upload part destinations on deactivation and narrow cancellation; no export file or log content changed.",
    "sources": {
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/coordinator.py": "0fbcc48fcd785e870d468782352ebca63778e76e184d9e4e197cfdc6d9c1663e",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7"
    }
  }
}
---

Source evidence for [the canonical guide](../../PRIVACY.md).
