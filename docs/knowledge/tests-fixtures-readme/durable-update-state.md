---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.durable-update-state",
  "title": "Captured history and local outcomes across native updates",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "durable-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected exact captured GLB staging, upload receipts, generation mesh binding, successful/failed/unfinished local application history and rejection of another reuse claim before update, after native update and after offline restart. Unit checks use actual storage APIs and detect missing bindings/history or an incorrectly accepted replay. Expanded package-mode probe passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with exact candidate SHA256 8ca0588625fc7597534e2e5bc98993c040de8b5bdc91e1893152d19bbbd80d5c; the synthetic predecessor changes only version declarations. Normal profiles remain unchanged, temporary profiles are removed and Scenario service connections are rejected. Existing seven records across two credential scopes and six selected job states remain; four upload records now include one captured mesh and the completed job retains three local claims. The mesh is existing first-party GPL fixture data, not provider output or a live source-object proof. This requires current captured-source/local-reuse storage APIs, not prototype migration. Published release-pair compatibility, hosted HTTPS/provenance, native GUI interaction, other OS runtime results and full release acceptance remain separate. No package/service/dependency behavior changed.",
    "sources": {
      "tests/blender/package_update.py": "11b620f11bc64a93e9ca11fa24a2effc03964a0ed9a5f9852e63abdc250a2e87",
      "tests/unit/test_repository_update_runner.py": "be732a18b2450dabe224e202c2ef8e08e16def177d7c1732d15a654bf9512a16",
      "tools/test_repository_update.py": "45fa8e414ac1436f09f01f17808be7f1c49e35080a6bd471fe2681c7bfc327ca",
      "scenario/core/jobs/store.py": "8a28fe796ea668eb525386e9e6400ab528f1c305cf6b7a488c4ff14e0d04eb35",
      "scenario/core/jobs/upload_store.py": "e5a609291095c112a00184d99795d8d21c177ddc6bc801a5c113bb489df27053",
      "scenario/core/jobs/mesh_source.py": "6448123e64f6d3f012de62b714f2fcffdeb173d530f6fd316d4022f354595229",
      "tests/fixtures/synthetic/static-triangle.glb": "35a1a3d3f5c875577f3bb97440ba0c9766d5ab5a0c8b54759e88569da47272f0"
    }
  }
}
---

# Captured history and local outcomes across native updates

Evidence for [the canonical guide](../../../tests/fixtures/README.md).
