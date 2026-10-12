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
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Inspected the bpy-free format registry, import-unit grouping with and without SDK 2.2.0 metadata.type/parentId lineage (peer counts include oversized files; model children of a material stay separate units; once a job holds a model file, every member is in exactly one unit's files, one glTF unit's candidate resources or one finding, a reported file is never a companion or candidate resource, and leftovers are ambiguous-package beside several OBJ or glTF files without lineage and unbound otherwise, including maps whose stored role has no MTL slot and files under a skipped or unsupported model; a seeded randomized unit test checks this over 3,000 synthetic manifests), primary ordering with companion and size tie-breaks, size bounds, format signatures, LF-only PLY header routing with unique elements and unique properties per element, per-physical-line OBJ and MTL reference rewriting with fixed report keywords, byte-based cancellation, MTL option values limited to plain ASCII decimal numbers and -bm 1 added to a bound normal statement that keeps no -bm, and JSON glTF URI binding keyed by resource kind with a length check for every buffer, base64 data URIs with a supported media type and optional RFC 2397 attribute=value parameters before ;base64, and an alignment test against inspect_glb, with offline unit tests over synthetic manifests and files only. Ad-hoc isolated factory-startup checks on Blender 5.0.1, 5.1.2 and 5.2.1 showed that Blender continues an OBJ statement after a backslash and trailing whitespace, that rewritten MTL files with a trailing backslash load only the snapshot texture, and that the kept option value forms tested (1, -1, +1, 1., .5, -.5, +.5, 1.5e3, 1E-3, 1e+3, 007 and 1e39) resolve the map to the snapshot texture after rewriting, while the earlier output for -s 1_0 did not. An ad-hoc check on Blender 5.1.2 showed that a canonical texture name missing from the snapshot is loaded from the process working directory, so the snapshot precondition is documented, not enforced here. The bundled glTF importer source in Blender 5.0.1, 5.1.2 and 5.2.1 decodes buffer and image data URIs from the first ;base64, and otherwise reads the URI as a file path, so other data URIs fail closed here. These checks are not repeatable native tests. GLB import, inspect_glb and the stored manifest are unchanged; lineage is not persisted, no planned store migration includes it and no issue tracks that follow-up yet. No UI, MCP, session, importer, worker, claim or native Blender wiring, no SPZ/PLY splat decoding and no live provider evidence for package shapes, MIME aliases, SPZ versions or glTF delivery. On 2026-10-10 the section's integration sentences were updated: the saved-package-import topic reviews how saved model package import offers and claims these units. These claims and the review date are unchanged. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 rewrite_mtl began adding -bm 1 to a bound map_Bump, bump or norm statement without a kept -bm: isolated background imports on Blender 5.0.1, 5.1.2 and 5.2.1 showed that the OBJ importer otherwise gives the Normal Map node Strength 0. Unit tests cover the three keywords with and without a saved -bm, including -bm 0; the new test failed before the change. Only the rewrite_mtl statements were re-reviewed on that date, against main at its base revision after the stack was rebuilt there; the other statements keep their earlier review.",
    "sources": {
      "scenario/core/scene/model_formats.py": "da33dd578b40705e9ddd79bc69afe9984b07f2f3e43764ce94b02aa7a6639a15",
      "scenario/core/scene/model_references.py": "0431633b34f6f77b52b971dc657803f63ecafda3bd7cbd6c14e8ddbd572913da",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "tests/unit/test_model_formats.py": "00bfa89a675ed2a301e13e5bfc587b6ed81ce953ef00ebe842253e5db8b5cfa5",
      "tests/unit/test_model_references.py": "20381ad1f546ef847e163d36d41842f1d8abe2fa35bef7878758c7447c291ded",
      "tests/unit/test_glb.py": "361bd8095611ec198c7f8af6329aaaa5475fa074fe67cb71038759a813f3f626",
      "tests/fixtures/synthetic/static-triangle.glb": "35a1a3d3f5c875577f3bb97440ba0c9766d5ab5a0c8b54759e88569da47272f0"
    }
  }
}
---

# Saved 3D package classification

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-3d-package-classification).
