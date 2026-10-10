---
{
  "type": "Evidence",
  "id": "docs-mesh-application.saved-package-import",
  "title": "Saved model package import",
  "description": "Main-thread snapshot preflight, staged import and rollback for saved GLB, glTF, FBX, OBJ and mesh PLY units.",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected model_application.prepare_snapshot: main-thread only; members opened without following links, read once and required to equal each receipt's size and SHA-256 before any decoder message; canonical snapshot names in a private directory under the user model-import folder; GLB inspect_glb, JSON glTF inspect_gltf_json with the unit's candidate resources and rewritten URIs, OBJ rewrite_obj and MTL rewrite_mtl with every bound map copied, binary FBX signature with a bundled FBX add-on check, PLY routed by splat_ply classify so splat PLYs stop; PNG, JPEG and WebP head checks; a window requirement for FBX, OBJ, PLY and rigged glTF; the snapshot removed on any failure. Inspected import_snapshot: single use, one staging importer per format with unique material names and no FBX image search, staging selection cleared, an image guard that keeps only packed images or files inside the snapshot, the FBX frame-rate mismatch for clips, the frame-zero anchor, publication with scenario_assets and rollback verified over objects, collections, meshes, materials, node groups, images, cameras, lights, armatures, actions, scenes, curves, textures and shape keys. Inspected JobSession.apply_recovered_model: reclassification from the verified record, the preflight before the claim, every member in the claim and unchanged receipt retry, plus the model/glb, FBX application/* and model/mtl local name aliases. Installed tests build OBJ with MTL and PNG, embedded-texture FBX, separate glTF with its buffer and PNG, and mesh PLY fixtures with Blender's own exporters, and cover placement, preserved selection, packed images, dropped maps, external FBX textures, a disabled FBX add-on, ASCII FBX, out-of-package glTF URIs, splat PLY and SPZ refusal, changed bytes, windowless callers, rollback, single use, the model/glb alias, animated GLB timing and runtime journeys with every member in reuse claims. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). Blender 5.0 and 5.2, Linux and Windows CI, live provider packages, glTF JSON delivery, physical desktop interaction and release acceptance are not established; copying and hashing stay synchronous on the main thread.",
    "sources": {
      "scenario/blender/model_application.py": "77c373fe556c7dd66dd47c70b8602254c56c66f9e678e4e489d61c6a6dabef17",
      "scenario/blender/job_session.py": "07eb472d0ecdc831cb3491b6f7c521436736e138db86a5dd35ed404f83d000a3",
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/core/scene/model_formats.py": "5cccc357bab6dea268ba2940cf3a8bd2b1688322f5fa7a8c09229f06b3d05aaf",
      "scenario/core/scene/model_references.py": "e045878d3d7913843b32c784d7e3fd97f54f774f4e6066d0c36ee7564eca1e14",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/core/config.py": "933d9838304f903e2ab79fb60bbab76f999d12b76e9bd8a8525cd27c1f8ccee7",
      "tests/blender/test_model_packages.py": "75f5753a8b5efcfdddabfe0197848ef155eb863543ddf60aea041f5243f31388",
      "tests/blender/helpers.py": "de37b0e824aa87878cd911289f7e40ce280857001f8dbd86babfa99e30faa635",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3",
      "tests/unit/test_config.py": "e1818a355f6d9fb244cb3badf137a89a340d3f7f8664ab2fe73655eb38fc6125"
    }
  }
}
---

# Saved model package import

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-model-package-import).
