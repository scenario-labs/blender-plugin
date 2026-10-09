---
{
  "type": "Evidence",
  "id": "docs-result-transfers.splat-preparation",
  "title": "Worker-side splat preparation",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "splat-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed bounded SPZ v2/v3, 3DGS PLY and .splat decoding, explicit SPZ v1 and v4 rejection, receipt-bound hashing while decoding, file identity and record rechecks, and the snapshot format. Offline unit tests use synthetic files only, including seeded mutation checks and a loose 2,000,000-point timing smoke. A synthetic installed-ZIP test decodes off the main thread and builds point meshes through read-only foreach_set views. Isolated Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 probes recorded decode and build timings for one run, not a guarantee. No provider files, live MIME, SPZ version, axis or original-file evidence, SPZ v4 decoding, session, UI or MCP wiring, scene claim, splat builder or release acceptance. Format references are the public nianticlabs/spz loader and antimatter15/splat converter.",
    "sources": {
      "scenario/core/scene/splats.py": "5cc9dc32ff65b595794cf609283828f17d683e40f23434f654b7a82fe48018a2",
      "scenario/core/scene/spz.py": "7337b2a3251209f90d3d555eaf2845367fc73e3a918b73f4c00854633e0a2b7b",
      "scenario/core/scene/splat_ply.py": "8fd67892bddc94c391beb7bee4ada0ffcc4d02594f665299a639a1a11e0ae25c",
      "scenario/core/jobs/results.py": "348766da097df428012b4f119a170d2fa6cb628106f107c264c727965c8d6409",
      "scenario/core/jobs/coordinator.py": "3807613afe3c4b8a3cb25e0e3862fbfabdd80ad649c7a96769c5a218dc60872a",
      "scenario/core/jobs/workers.py": "2d7b0820062d5a702d742f64fa25fd6c9ca472f0d1f258c7ea8fd17f81a2ba0a",
      "scenario/core/jobs/upload_sources.py": "5beb6a3a8a5c4ab696e6a8aff78426c4b6615b9256599a59fbad30ac56cc388e",
      "tests/unit/splat_files.py": "1c5e9c81ff185f1048c34f25dd4ca1de30a206c3a2b6c2aaf8ae5a83219d9704",
      "tests/unit/test_splats.py": "6da2eb6fce0396f705d5c1702313e5a2a6f2ce54113c3a366a07c53323a31246",
      "tests/unit/test_spz.py": "801d45f6180f2e2cab0086d52c166eb26f8cf06885cddc223478d35a67c00d1f",
      "tests/unit/test_splat_ply.py": "135f9dc62febb44ab9d26df2cdc17d5fe5143874011ed2152deb9ce5e0a80d53",
      "tests/unit/test_model_import_preparation.py": "055c358f70e25fb550acbb59b93e557c4e1e55737aee6709d0ebe7db9214295e",
      "tests/blender/test_splat_snapshots.py": "ebf534ac87ef5a605dd01db91736b37ea7b740f910abd50dbc183349975593d7",
      "tests/blender/run_all.py": "18877a4e72c1b8ee16747d0cf7b669a72a5a3bef098566e656b2a5bada003034"
    }
  }
}
---

# Worker-side splat preparation

Evidence for [the canonical guide](../../RESULT_TRANSFERS.md).
