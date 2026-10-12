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
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected model_application.prepare_snapshot: main-thread only; members opened without following links, read once and required to equal each receipt's size and SHA-256 before any decoder message; canonical snapshot names in a private directory under the user model-import folder; GLB inspect_glb, JSON glTF inspect_gltf_json with the unit's candidate resources and rewritten URIs, OBJ rewrite_obj and MTL rewrite_mtl with every bound map copied and -bm 1 added to a bound normal statement that keeps no -bm, binary FBX signature with a bundled FBX add-on check, PLY routed by splat_ply classify so splat PLYs stop; PNG, JPEG and WebP head checks; a window requirement for FBX, OBJ, PLY and rigged glTF; the snapshot removed on any failure. Inspected import_snapshot: single use, one staging importer per format with unique material names and no FBX image search, staging selection cleared, an image guard that keeps only packed images or files inside the snapshot, Non-Color data for the bound normal, roughness and metallic OBJ maps from the unit's saved texture roles (ImportUnit.texture_files and NON_COLOR_TEXTURE_ROLES) with albedo left sRGB, a Normal Map node added only when a normal map does not already reach the shader through one, the importer's Normal Map node taking its Strength from the rewritten -bm, the FBX frame-rate mismatch for clips, the frame-zero anchor, publication with scenario_assets and rollback verified over objects, collections, meshes, materials, node groups, images, cameras, lights, armatures, actions, scenes, curves, textures and shape keys. Inspected JobSession.apply_recovered_model: reclassification from the verified record, the preflight before the claim, every member in the claim and unchanged receipt retry, plus the model/glb, FBX application/* and model/mtl local name aliases. Installed tests build OBJ with MTL and PNG, embedded-texture FBX, separate glTF with its buffer and PNG, and mesh PLY fixtures with Blender's own exporters, and cover placement, preserved selection, packed images, dropped maps, Non-Color OBJ normal, roughness and metallic maps with an sRGB albedo and one Normal Map node at Strength 1 from a saved map_Bump without -bm, a saved bump -bm 0.5 kept as Strength 0.5, normal-map routing for a map linked straight into Normal or left unlinked, external FBX textures, a disabled FBX add-on, ASCII FBX, out-of-package glTF URIs, splat PLY and SPZ refusal, changed bytes, windowless callers, rollback, single use, the model/glb alias, animated GLB timing and runtime journeys with every member in reuse claims. Plain Blender 5.0.1, 5.1.2 and 5.2.1 OBJ imports read every MTL map as sRGB and add the Normal Map node themselves; the new native test failed on Metallic and Roughness colorspace before the fix. Isolated background imports on those three versions give the importer's Normal Map node Strength 0 for map_Bump or bump without -bm, 1 with -bm 1 and 0.5 with -bm 0.5; the native Strength assertion failed with 0.0 before rewrite_mtl added the default. The full installed suite passed 1,256 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 (exact ZIP SHA-256 54cc6483f7ef1f3d94f4af5fee44dffc3144be96758604b5c5c2a1954d4ed2b1), and the installed baseline passed 778 tests with the same 2 skips on macOS arm64 Blender 5.0.1 and 5.2.1 from separate builds of the same checkout. The full suite on Blender 5.0 and 5.2, Linux and Windows CI, live provider packages, glTF JSON delivery, physical desktop interaction and release acceptance are not established; copying and hashing stay synchronous on the main thread. On 2026-10-12 only the OBJ normal strength statements and the test results were re-reviewed; the other statements keep their 2026-10-10 review.",
    "sources": {
      "scenario/blender/model_application.py": "c7fff225f53b796c0206ef4d3ba69ca4ff077d8cfdb3bc062dfbd4051ab3e0a3",
      "scenario/blender/job_session.py": "07eb472d0ecdc831cb3491b6f7c521436736e138db86a5dd35ed404f83d000a3",
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/core/scene/model_formats.py": "da33dd578b40705e9ddd79bc69afe9984b07f2f3e43764ce94b02aa7a6639a15",
      "scenario/core/scene/model_references.py": "990f3827f3a94d17073dd5c9dab8081292e2207c7ff268aff690b344616d90ba",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/core/config.py": "933d9838304f903e2ab79fb60bbab76f999d12b76e9bd8a8525cd27c1f8ccee7",
      "tests/blender/test_model_packages.py": "8ebac60fc363667ba061930806f658149c8d1649750ccd2e0b2670ec1fa963e0",
      "tests/blender/helpers.py": "de37b0e824aa87878cd911289f7e40ce280857001f8dbd86babfa99e30faa635",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3",
      "tests/unit/test_config.py": "e1818a355f6d9fb244cb3badf137a89a340d3f7f8664ab2fe73655eb38fc6125",
      "tests/unit/test_model_formats.py": "00bfa89a675ed2a301e13e5bfc587b6ed81ce953ef00ebe842253e5db8b5cfa5"
    }
  }
}
---

# Saved model package import

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-model-package-import).
