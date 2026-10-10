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
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the bpy-free format registry, import-unit grouping with and without SDK 2.2.0 metadata.type/parentId lineage (peer counts include oversized files; model children of a material stay separate units; once a job holds a model file, every member is in exactly one unit's files, one glTF unit's candidate resources or one finding, a reported file is never a companion or candidate resource, and leftovers are ambiguous-package beside several OBJ or glTF files without lineage and unbound otherwise, including maps whose stored role has no MTL slot and files under a skipped or unsupported model; a seeded randomized unit test checks this over 3,000 synthetic manifests), primary ordering with companion and size tie-breaks, size bounds, format signatures, LF-only PLY header routing with unique elements and unique properties per element, per-physical-line OBJ and MTL reference rewriting with fixed report keywords, byte-based cancellation and MTL option values limited to plain ASCII decimal numbers, and JSON glTF URI binding keyed by resource kind with a length check for every buffer, base64 data URIs with a supported media type and optional RFC 2397 attribute=value parameters before ;base64, and an alignment test against inspect_glb, with offline unit tests over synthetic manifests and files only. Ad-hoc isolated factory-startup checks on Blender 5.0.1, 5.1.2 and 5.2.1 showed that Blender continues an OBJ statement after a backslash and trailing whitespace, that rewritten MTL files with a trailing backslash load only the snapshot texture, and that the kept option value forms tested (1, -1, +1, 1., .5, -.5, +.5, 1.5e3, 1E-3, 1e+3, 007 and 1e39) resolve the map to the snapshot texture after rewriting, while the earlier output for -s 1_0 did not. An ad-hoc check on Blender 5.1.2 showed that a canonical texture name missing from the snapshot is loaded from the process working directory, so the snapshot precondition is documented, not enforced here. The bundled glTF importer source in Blender 5.0.1, 5.1.2 and 5.2.1 decodes buffer and image data URIs from the first ;base64, and otherwise reads the URI as a file path, so other data URIs fail closed here. These checks are not repeatable native tests. GLB import, inspect_glb and the stored manifest are unchanged; lineage is not persisted, no planned store migration includes it and no issue tracks that follow-up yet. No UI, MCP, session, importer, worker, claim or native Blender wiring, no SPZ/PLY splat decoding and no live provider evidence for package shapes, MIME aliases, SPZ versions or glTF delivery.",
    "sources": {
      "scenario/core/scene/model_formats.py": "ca21f03a73eca15b479e858b40e55ebcee1907e96aa47038da5c64389c764bfb",
      "scenario/core/scene/model_references.py": "bb1522759fb741bad331f41b1894808ae289ed29d0a236bb7bc9f79d418c4693",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "tests/unit/test_model_formats.py": "85bb70275db0d6471e4b7fd25bb5a3e0f33e44e9f6f8a1b755a7409a7e2a95fb",
      "tests/unit/test_model_references.py": "96407240c109daf650e06e6958c9cf30135e562fa5e575ee3498b1267336159d",
      "tests/unit/test_glb.py": "361bd8095611ec198c7f8af6329aaaa5475fa074fe67cb71038759a813f3f626",
      "tests/fixtures/synthetic/static-triangle.glb": "35a1a3d3f5c875577f3bb97440ba0c9766d5ab5a0c8b54759e88569da47272f0"
    }
  }
}
---

# Saved 3D package classification

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-3d-package-classification).
