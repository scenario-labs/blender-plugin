---
{
  "type": "Evidence",
  "id": "docs-development-validation.durable-update-state",
  "title": "Captured history and local outcomes across native updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "durable-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "ea77f3a542be698301bd0a414579d4a9e40650bb",
    "limits": "Reviewed preservation of exact captured GLB staging and receipts, generation mesh bindings, nonempty texture roles, credential isolation and successful/failed/unfinished local applications through native update and offline restart. The probe requires another reuse claim to fail without changing the unfinished record. The integrated candidate a2254eb9ae5b24608eacf1e850dbbb95d9a1e4ff7b6b4b881bd4de2ef5e56610 and synthetic predecessor 743ef2b13be765e5104f8c87f53e787b6358d58d468d90ea142f464d62b0d3b4 passed macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Each snapshot retained seven jobs across two credential scopes, four uploads, two mesh-bound jobs and three local outcomes. Installed archive bytes, enabled state, saved scene and original sources were checked; service requests remained zero, loopback servers stopped, owned profiles were removed and the normal profile was unchanged. Film bindings and the separate Film upload association are explicitly empty in this candidate, so these runs do not establish Film acceptance. The probe also seeds and compares those fields when the installed package exposes the Film APIs, including a cross-scope rejection check. Earlier recorded Film-capable evidence used candidate 100d6fbb4707748b7514b26ec3cb0d456f9a7b673ce08108de2181b0b3cab674 and synthetic predecessor 2727ec724855930429282864d094ee048790af778f884cf7ac7c801c70e0a5b7 on the same three Blender series; that is evidence for those historical artifacts, not this candidate. Unit regressions detect lost mesh bindings, lost uncertainty, allowed replay, changed or missing Film upload identity and scope leakage. The GLB is first-party GPL fixture data, not provider output or live object authority. Synthetic predecessors change only version declarations. Published release-pair compatibility, hosted HTTPS/provenance, physical desktop updates, other OS runtime results and full release acceptance remain separate. No package, service or dependency behavior changes.",
    "sources": {
      "tests/blender/package_update.py": "0e919d39511b395450f71997be01d32eaed4700b77bf55fa87786b185b7ea6d5",
      "tests/unit/test_repository_update_runner.py": "d615195d1166a0d70bdbf01591ec14545e49e5a3fbaa4267b7122f2d29d512a1",
      "tools/test_repository_update.py": "45fa8e414ac1436f09f01f17808be7f1c49e35080a6bd471fe2681c7bfc327ca",
      "scenario/core/jobs/store.py": "f8095b6cd7d26d8ce11725dbba73b8b0a329c3bd9c2297496462d9ba4e4e3d8e",
      "scenario/core/jobs/upload_store.py": "e5a609291095c112a00184d99795d8d21c177ddc6bc801a5c113bb489df27053",
      "scenario/core/jobs/mesh_source.py": "6448123e64f6d3f012de62b714f2fcffdeb173d530f6fd316d4022f354595229",
      "tests/fixtures/synthetic/static-triangle.glb": "35a1a3d3f5c875577f3bb97440ba0c9766d5ab5a0c8b54759e88569da47272f0"
    }
  }
}
---

# Captured history and local outcomes across native updates

Evidence for [the canonical guide](../../development/validation.md).
