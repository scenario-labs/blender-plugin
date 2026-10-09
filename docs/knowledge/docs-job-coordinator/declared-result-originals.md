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
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed ResultCommands.load_manifest and _download through the coordinator: EXR originals of image assets are saved instead of previews with unknown size, refreshes reuse the saved source and never acquire a new projection, and missing or changed declarations stop before transfer. Synthetic SDK responses and mocked storage only; no new SDK method, retry or worker change.",
    "sources": {
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "tests/unit/test_result_commands.py": "e4640308f9f2f8fb26d518741d188f10bd2b480fda1ef82292b1d9f23255299e",
      "tests/blender/test_result_commands.py": "67841d71c2b37c02b9bd1d0d9fe911aecb8e902d3116c33abee1462390a4dc53"
    }
  }
}
---

# Result manifests with declared EXR originals

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
