---
{
  "type": "Evidence",
  "id": "docs-mesh-application.saved-package-classification",
  "title": "Saved 3D package classification",
  "description": "Bpy-free import units, ordering and reference plans for saved non-GLB 3D results.",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "saved-package-classification",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the bpy-free format registry, import-unit grouping with and without SDK 2.2.0 metadata.type/parentId lineage, primary ordering, size bounds, format signatures, PLY header routing, streaming OBJ and MTL reference rewriting and JSON glTF URI binding, with offline unit tests over synthetic manifests and files only. GLB import, inspect_glb and the stored manifest are unchanged; the lineage fields are not persisted until a store v10 migration. No UI, MCP, session, importer, worker, claim or native Blender wiring, no SPZ/PLY splat decoding and no live provider evidence for package shapes, MIME aliases, SPZ versions or glTF delivery.",
    "sources": {
      "scenario/core/scene/model_formats.py": "aecaebdec4ee9f5ad77dc3de565c1fdd62065ca65e0a66684e5ced91669c6ed1",
      "scenario/core/scene/model_references.py": "91e48680ae9f7f4f03afd4fd5317ef03da7e1ae6cedccf08f03fc4de3a6e695a",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "tests/unit/test_model_formats.py": "b53222b3be246e091adab16cf9f62d931615bc8001733467e941365acf77df96",
      "tests/unit/test_model_references.py": "07ad59e6598099ab10ba55ed05787e186b63c3b8f361942f816ba8ad84cab0e8",
      "tests/unit/test_glb.py": "361bd8095611ec198c7f8af6329aaaa5475fa074fe67cb71038759a813f3f626",
      "tests/fixtures/synthetic/static-triangle.glb": "35a1a3d3f5c875577f3bb97440ba0c9766d5ab5a0c8b54759e88569da47272f0"
    }
  }
}
---

# Saved 3D package classification

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-3d-package-classification).
