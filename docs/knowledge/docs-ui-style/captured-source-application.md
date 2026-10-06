---
{
  "type": "Evidence",
  "id": "docs-ui-style.captured-source-application",
  "title": "Captured mesh source application",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "captured-source-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "e156d350cd282bfbcda98b378b4f6c88fd608fd7",
    "limits": "Inspected export-time live static-mesh guards, exact persisted input binding, single-source UI/MCP approval, source revalidation and session retirement. Installed synthetic tests and isolated macOS arm64 Blender 5.1.2 desktop interaction cover original-source selection despite a different active object, cancellation, confirmation and preservation of the other mesh. The exact ZIP and interaction limits are recorded in UI_STYLE. Provenance alone cannot recreate authority after undo/load/restart. Provider alignment, rigs/retexture/segmentation, multi-source selection, global undo, persistent restoration, other OS desktop behavior and release acceptance remain incomplete. No new SDK operation or paid test; other topic records retain their own scope. Current-base integration verifies export provenance with the export fingerprint while retaining the separate strict edit fingerprint. Native regression rejects an edit-format digest substituted into export metadata without adding source authority, and keeps the valid binding usable. The integrated ZIP a2254eb9ae5b24608eacf1e850dbbb95d9a1e4ff7b6b4b881bd4de2ef5e56610 also passed the same isolated macOS arm64 Blender 5.1.2 mouse, Escape, viewport-focus and Return interaction. The unchanged active mesh and transport counts, original copy, verified installed bytes, zero socket attempts and unchanged normal profile were checked. Earlier screenshots retain their original artifact attribution. This does not establish other OS desktop behavior or release acceptance.",
    "sources": {
      "scenario/blender/mesh_provenance.py": "32060933d3e50e2b67b35b4c2287f67f01fa6021a9371d47bd658a41d92008d5",
      "scenario/blender/job_session.py": "9ea9f2f86649c73a70dded9a582bb76504fb73a9b774ada62ed594457dc18c3c",
      "scenario/blender/model_jobs.py": "7af0104a9184382c70d69ed6c1ba3a926b8edfa5930fa5f7cc3d6b79c35d1d21",
      "scenario/blender/job_recovery.py": "97c4ca8fe660dc2b0bb62c12315e26d1719cf178b59d5f97a6efc5ff0e391553",
      "scenario/blender/runtime.py": "fad8c3b706e8826740c57c357052099fcad3e6b147e0acc9ee95332ce6ea2fc5",
      "scenario/blender/mesh_application.py": "99e0af39cd720903982dee3480a20dd25164f318ca14d2550b4fc31ed8e6d935",
      "scenario/blender/mesh_result_application.py": "5b23cc19ffa6a240bb97b686bbbd1c0f18d5caf50191598aab5a6c32b9ce3de7",
      "scenario/mcp/tools_scenario.py": "48b084e7e0e730745c09c1070075e7b839a2fc8be94394d4b8a733036ee09e12",
      "tests/blender/test_model_generation.py": "1a4a63807077e29ab90178f8a9e37960cbd2386787c9fc56dec0e799d0290b74",
      "tests/blender/test_reference_uploads.py": "af02638c191b6462b1be28ffc2c9a5fbcfda11203af72a962a66f77b2ac1c6dc",
      "docs/images/captured-mesh-source-approval.png": "7e5417cc889098876cfff99cd5fd44b1365e12fd3da9bf8608bee8116db5aafb",
      "docs/images/captured-mesh-source-result.png": "6f33c3027df4f968080dfe23ddce58882d07f66ea646990ad711baa7c68ac9ae",
      "scenario/blender/mesh_export_fingerprint.py": "55b40c165f83667d87f61e9007c2fb7fac0097b5d7e90d1dba7ae33ff293dd62"
    }
  }
}
---

# Captured mesh source application

Evidence for [the canonical guide](../../UI_STYLE.md).
