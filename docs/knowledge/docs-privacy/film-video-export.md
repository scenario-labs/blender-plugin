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
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Inspected the export destination, private staging contents, the single local log line with basename and SHA-256, and crash leftovers next to the destination. No network activity is involved; no legal-policy audit. Re-reviewed after the hidden partial file moved to a fixed .scenario-<hex>.partial name and destinations inside staging, extension or Blender user storage became refused; the privacy wording remains accurate. Re-reviewed after the placeholder pin, free-space checks and private-root folding; no new file or log content, and the wording remains accurate. Re-reviewed after the rebase onto 72723f02, whose coordinator changes retire upload part destinations on deactivation and narrow cancellation; no export file or log content changed. Re-reviewed after the bounded export shutdown: an export abandoned at exit while blocked on file access can leave the empty placeholder the guide already names, and the new warning names no path. Re-reviewed after the rebase onto 7fb15252, whose coordinator changes add trained-model route checks before quoting and preview-lane commands; no export file or log content changed, and the merged preview cache wording now precedes the export wording in the same paragraph.",
    "sources": {
      "scenario/blender/local_capture.py": "d1d3a5bde72ca1f61bf879fbc971bbca59d344e31a6a5c96e42558148537a43d",
      "scenario/core/jobs/coordinator.py": "8a93052389141a9432378db73c944023c024bfafa64d8667b2a854b27253fe7c",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4"
    }
  }
}
---

Source evidence for [the canonical guide](../../PRIVACY.md).
