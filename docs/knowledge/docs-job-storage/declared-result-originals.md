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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ResultAsset source (asset or original, original only for image/x-exr and image/aces) and projection (equirectangular only, image media only), strict current schema keys and the manifest command that selects EXR originals of image assets with unknown size, whose download then requires the storage response's Content-Length (missing length leaves no receipt). Unit and installed-ZIP tests use synthetic SDK responses and mocked storage. The labels do not authorize World application, measure dynamic range or replace Blender decoding; World application keys on the saved media type and runs its own container and primaries checks for both labels. Live HDRi asset layout, original host, size and Content-Length are unverified.",
    "sources": {
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "scenario/core/jobs/result_metadata.py": "775986522c43e4b837f3deb333f964ca721eb6b8c74bd0282f40824a19c4af17",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "tests/unit/test_job_store_schema10.py": "2987b1dcc859a30a2fe4ab1a922da74fa4ca1e6e56d0509f3639eee648d1bac7",
      "tests/unit/test_result_metadata.py": "7de18feef6672a981fdbb80e091cf0fc9f6dc752bdefd1553d4afd9b8dea3307",
      "tests/unit/test_result_commands.py": "5399126ac8f7255fc8ad569f03bf47a16f91fb986757aefeffa7e858cc707cc5",
      "tests/blender/test_result_commands.py": "7601fdc6e62e273aed7b1552dfba86a9928b21e3e97573e8ccfab0d57823404c",
      "scenario/blender/world_application.py": "341b67665ec8be9201c3191559d47a31421aae5726bc2ea06b134f8245876895"
    }
  }
}
---

# Declared EXR originals and server projections in result manifests

Evidence for [the canonical document](../../JOB_STORAGE.md).
