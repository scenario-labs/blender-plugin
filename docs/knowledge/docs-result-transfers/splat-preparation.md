---
{
  "type": "Evidence",
  "id": "docs-result-transfers.splat-preparation",
  "title": "Worker-side splat preparation",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "splat-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed bounded SPZ v2/v3, 3DGS PLY and .splat decoding, explicit SPZ v1 and v4 rejection, the kept SPZ antialiasing and extension flags (extension records are not read), header bounds and their attribution, mesh PLY classification and fail-closed rejection of other PLY layouts including the PlayCanvas compressed PLY, receipt-bound hashing while decoding (including a decodable change to bytes the decoder read), cancellation before each receipt hash, file identity and record rechecks, and the snapshot format. Checked that the prototype read_spz rejects SPZ v1, v4, empty and over-limit files and that the prototype Add to scene operator reports such a SplatError and adds no object, because import_spz decodes before creating Blender data. Offline unit tests use synthetic files only, including seeded mutation checks, a synthetic coordinate-system extension record and a loose 2,000,000-point timing smoke. A synthetic installed-ZIP test decodes off the main thread and builds point meshes through read-only foreach_set views; another installed-ZIP test calls the Add to scene operator with SPZ v1 and empty files and checks the error report. Isolated Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 probes recorded decode and build timings for one run, not a guarantee. No provider files, live MIME, SPZ version, flag, axis or original-file evidence, SPZ v4 decoding, session, UI or MCP wiring, scene claim, splat builder or release acceptance. Format references are the public nianticlabs/spz loader and extension guide, the antimatter15/splat converter and the playcanvas/splat-transform compressed PLY reader.",
    "sources": {
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/scene/spz.py": "dab0ca7fd16ca7dd9366d1c52e64513dd06bb78d1b82bd3dbe887ce9e59bff0a",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "scenario/core/jobs/results.py": "f316fc3fb9e8799ce1aa0cc679ca8870c8b40239b6fb12c022ce1548de63169a",
      "scenario/core/jobs/coordinator.py": "62d13ea128834a15d1355dc32f628bb63413e171f6a0946ef9736410e7ede541",
      "scenario/core/jobs/workers.py": "3d840e62059f7c4caa9a0892f9856d077cbfe63074190521f1dfe61c8e234034",
      "scenario/core/jobs/upload_sources.py": "711517b315c8aca80f154ceecabc64f4c3d3b67c25e5304191c71b6a1ee617e4",
      "tests/unit/splat_files.py": "7a65dde984af9f98d1596a2e9d7fe0b8878f0fd31d8fc29f5120f0a26abc16d4",
      "tests/unit/test_splats.py": "29b853820fdc23f054b288ac71f0f02b3089f90ec4fcab67c5c91df3552a7866",
      "tests/unit/test_spz.py": "07e5ba1dd1cd710cdc1e18c1de9de5ea56ea1b03e9e57d06974fbdc6d02860ab",
      "tests/unit/test_splat_ply.py": "85a61a89f9983a6d69ca60b6ade7dff6234db0f66435c401218ab1893edffd19",
      "tests/unit/test_model_import_preparation.py": "cf65bbbce6f8366db9268b83c5efbcba9ac1567c8e30dab3dd014f8cbd1899af",
      "tests/blender/test_splat_snapshots.py": "a005350703b7e8a4e8821f6e7ae54b1e124968d6cc6e7cae682cb6d83f0e40f7",
      "tests/blender/run_all.py": "abe379e562470d288a302fa435515d08a1c2478457217a019d3cf6a5eb938c4d",
      "scenario/blender/operators.py": "eb6799a951e35124efcee45c2b25579de5b3074712eb2b549d1dc10972e2d265",
      "scenario/blender/apply_3d.py": "563c404b3c5704eb35ae0f10fee8359f95d2e18011fa9b120e23037ad2eadfd7",
      "scenario/blender/apply_splat.py": "a1cfdbfdfabdb27c6ed736702c301f3928edad8a8736de3774f4229732117d80"
    }
  }
}
---

# Worker-side splat preparation

Evidence for [the canonical guide](../../RESULT_TRANSFERS.md).
