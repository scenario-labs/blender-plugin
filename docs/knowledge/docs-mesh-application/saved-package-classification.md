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
    "limits": "Inspected the bpy-free format registry, import-unit grouping with and without SDK 2.2.0 metadata.type/parentId lineage (peer counts include oversized files; model children of a material stay separate units), primary ordering with companion and size tie-breaks, size bounds, format signatures, LF-only PLY header routing with unique elements, per-physical-line OBJ and MTL reference rewriting with fixed report keywords and byte-based cancellation, and JSON glTF URI binding with an alignment test against inspect_glb, with offline unit tests over synthetic manifests and files only. An ad-hoc isolated factory-startup check on Blender 5.0.1, 5.1.2 and 5.2.1 showed that Blender continues an OBJ statement after a backslash and trailing whitespace and that rewritten MTL files with a trailing backslash load only the snapshot texture; it is not a repeatable native test. GLB import, inspect_glb and the stored manifest are unchanged; lineage is not persisted and no planned store migration includes it (#65). No UI, MCP, session, importer, worker, claim or native Blender wiring, no SPZ/PLY splat decoding and no live provider evidence for package shapes, MIME aliases, SPZ versions or glTF delivery.",
    "sources": {
      "scenario/core/scene/model_formats.py": "e15fe77d5e62264b70c126f5ff18f99ccc00f10cbeb227f6cd9afd9461363b25",
      "scenario/core/scene/model_references.py": "836f368e87307c0f45580a673f4dc31b63480cb6034e6eede73ef1d343b7c335",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "tests/unit/test_model_formats.py": "5d158aa03fe8700b40b1e9c2bafa9bc2b7104fdecc030c03c0b208ead22d8661",
      "tests/unit/test_model_references.py": "9f07551a6127adf0cc149a45e667dd9cc99f0eae2d54822557ebc0c73586c732",
      "tests/unit/test_glb.py": "361bd8095611ec198c7f8af6329aaaa5475fa074fe67cb71038759a813f3f626",
      "tests/fixtures/synthetic/static-triangle.glb": "35a1a3d3f5c875577f3bb97440ba0c9766d5ab5a0c8b54759e88569da47272f0"
    }
  }
}
---

# Saved 3D package classification

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-3d-package-classification).
