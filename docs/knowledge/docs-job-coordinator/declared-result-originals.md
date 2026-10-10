---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.declared-result-originals",
  "title": "Result manifests with declared EXR originals",
  "description": "Coordinator manifest and refresh rules for originals and projections.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "declared-result-originals",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ResultCommands.load_manifest and _download through the coordinator: EXR originals of image assets are saved instead of previews with unknown size, refreshes reuse the saved source and never acquire a new projection, missing or changed declarations stop before transfer, and an original served without Content-Length ends in download_failed with no receipt and completes on a retry of the same command once the length is declared. Synthetic SDK responses and mocked storage only; no new SDK method, retry or worker change.",
    "sources": {
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "tests/unit/test_result_commands.py": "5399126ac8f7255fc8ad569f03bf47a16f91fb986757aefeffa7e858cc707cc5",
      "tests/blender/test_result_commands.py": "7601fdc6e62e273aed7b1552dfba86a9928b21e3e97573e8ccfab0d57823404c"
    }
  }
}
---

# Result manifests with declared EXR originals

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
