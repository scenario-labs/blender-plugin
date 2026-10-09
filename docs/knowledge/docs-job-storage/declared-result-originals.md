---
{
  "type": "Evidence",
  "id": "docs-job-storage.declared-result-originals",
  "title": "Declared EXR originals and server projections in result manifests",
  "description": "ResultAsset source and projection fields and their strict validation.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "declared-result-originals",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed ResultAsset source (asset or original, original only for image/x-exr and image/aces) and projection (equirectangular only, image media only), strict current schema keys and the manifest command that selects EXR originals of image assets with unknown size. Unit and installed-ZIP tests use synthetic SDK responses and mocked storage. The labels do not authorize World application, measure dynamic range or replace Blender decoding; image/aces is not yet accepted by World application. Live HDRi asset layout, original host and size are unverified.",
    "sources": {
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "scenario/core/jobs/result_metadata.py": "00904085422404c9d6d6a81805ed9c86a224b73f4c59c8516bf0c2de894c8e0f",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "tests/unit/test_job_store_schema10.py": "2987b1dcc859a30a2fe4ab1a922da74fa4ca1e6e56d0509f3639eee648d1bac7",
      "tests/unit/test_result_metadata.py": "7de18feef6672a981fdbb80e091cf0fc9f6dc752bdefd1553d4afd9b8dea3307",
      "tests/unit/test_result_commands.py": "e4640308f9f2f8fb26d518741d188f10bd2b480fda1ef82292b1d9f23255299e",
      "tests/blender/test_result_commands.py": "67841d71c2b37c02b9bd1d0d9fe911aecb8e902d3116c33abee1462390a4dc53"
    }
  }
}
---

# Declared EXR originals and server projections in result manifests

Evidence for [the canonical document](../../JOB_STORAGE.md).
