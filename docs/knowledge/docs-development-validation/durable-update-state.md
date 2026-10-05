---
{
  "type": "Evidence",
  "id": "docs-development-validation.durable-update-state",
  "title": "Captured history and local outcomes across native updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "durable-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "b9e4add385239e9d10fc5ea36b31289aef11a3af",
    "limits": "Inspected preservation of nonempty texture roles, exact captured GLB staging and upload receipts, generation mesh bindings, successful/failed/unfinished local application history, and rejection of another reuse claim before update, after native update and after offline restart. The probe additionally seeds six Film task bindings and a separate captured-mesh Film upload association when the installed package exposes those APIs. It compares the complete association and rejects access from the other credential scope. Unit checks detect lost bindings/history, replay, changed or missing Film upload identity and scope leakage; Film snapshot unit fixtures are synthetic, while native tests use the actual installed package storage. Combined native update/restart passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with exact Film candidate SHA256 100d6fbb4707748b7514b26ec3cb0d456f9a7b673ce08108de2181b0b3cab674 and synthetic predecessor 2727ec724855930429282864d094ee048790af778f884cf7ac7c801c70e0a5b7. Each saved snapshot contains all six Film bindings, one Film upload association, two mesh-bound jobs, nonempty texture roles and three local application outcomes. Older non-Film candidate 8ca0588625fc7597534e2e5bc98993c040de8b5bdc91e1893152d19bbbd80d5c also passed Blender 5.1.2 with explicitly empty Film fields; that run does not establish Film coverage. Normal profiles were unchanged, disposable profiles removed and Scenario service connections rejected. Seven records across two scopes and four uploads remain. The GLB is existing first-party GPL fixture data, not provider output or live source-object authority. Both predecessors change only version declarations. Published release-pair compatibility, hosted HTTPS/provenance, desktop interaction, other OS runtime results and full release acceptance remain separate. No package/service/dependency behavior changed. After reconciling merged media application into this branch, non-Film candidate SHA256 3c4e958b6fc40b7ca11ea8965d37d3b47321f235cacfe125c7401256a4d9edbc passed the same update/restart probe on all three Blender series, with synthetic predecessor 09bc0744995ffe92c0da13f7564697d5f189934be4804ac8929e5c06cf59f4bc. This candidate also passed 585 installed tests on Blender 5.1.2; its Film fields remain explicitly empty. The probe source and Film-capable candidate used above are unchanged by that rebase.",
    "sources": {
      "tests/blender/package_update.py": "0e919d39511b395450f71997be01d32eaed4700b77bf55fa87786b185b7ea6d5",
      "tests/unit/test_repository_update_runner.py": "d615195d1166a0d70bdbf01591ec14545e49e5a3fbaa4267b7122f2d29d512a1",
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

Evidence for [the canonical guide](../../development/validation.md).
