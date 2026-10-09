---
{
  "type": "Evidence",
  "id": "docs-mcp.world-result-application",
  "title": "Saved panorama World approval and restoration",
  "description": "Shared native and MCP commands for explicit World application and guarded restoration.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "world-result-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected saved-result World application and restoration through the same native/MCP approval handles, receipt verification, captured scene/current-World guard, durable claim and receipt-only retry. Synthetic tests cover unchanged service request counts, changed destinations, invalid image dimensions, edited World preservation and separate restore approval. The exact ZIP is tested on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop confirms packing, separate mouse approvals, restoration, keyboard/viewport interaction, clean exit and unchanged normal profile. UI_STYLE.md records exact ZIP and test app identity qualification. Only ready/apply_failed saved PNG, JPEG or OpenEXR results (image/png, image/jpeg, image/exr, image/x-exr or image/aces) qualify; application rejects a container that differs from the saved media type, and the native dialog and MCP format field state that declared format. JPEG/ACES offers, the format text, dialog invoke/draw/cancel and local failures with retry state are covered by headless native tests; the 5.1.2 desktop capture predates them. Automatically imported/applied images cannot be reused through this job claim. Session-local restore is not global undo or restart persistence. No new API contract, cloud panorama preset, actual HDR range, seam/pole quality, paid provider acceptance, other OS desktop proof, #263 resolution, full #98 completion or release acceptance.",
    "sources": {
      "scenario/blender/world_application.py": "8c864f3b7b48fd77ff6a5b94dea86d586a6d312d5782f01f53c13cd893a853f9",
      "scenario/core/scene/panorama.py": "813bc6a891c955f67f3c9e345501ac558d662663fb4dbc98549b7ebbe02ecff9",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "scenario/blender/model_jobs.py": "7e9fd50f0fff4c0607a62099a64c93d3e94ba3fda04e1c64886b7eb3d37f593e",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/blender/job_recovery.py": "2b080003f719054742876dd88cc58db18ae6a8a30ad4aefd2d0daf94a0c4d81d",
      "scenario/mcp/tools_scenario.py": "29d00c5f120eaa9be1eed7c40e5d5aee0be63c77ee468418cdd8deb9b289a02c",
      "tests/blender/test_model_generation.py": "a723a275a14478a75ddf5912ae0af81208fe0acd8da2380d57c8aa065eb3c56b",
      "tests/blender/test_world_application.py": "c20c5a181cac26cb6c656cf58b85c4c985198b1dab928c71dfabd95ae9811a0e",
      "tests/blender/test_session_results.py": "e87afd949fda187702ddac63c0c52f2597fead62c171e2f2afcc9ab217defcf8",
      "tests/unit/test_panorama.py": "6f1f724c68ff3e49dd27b31c6277d146f0e60d3de8b684b60266c46da387b5c2",
      "docs/images/saved-world-approval.png": "84efcb774621c15e72798d45cffb74eb307831b7ccdc12ed6169198526604b65",
      "docs/images/saved-world-restore.png": "8c831fb5e0ad0a37735b3760a83a80a8b122b04452768fd166147dce6410c406"
    }
  }
}
---

# Saved panorama World approval and restoration

Evidence for [the canonical document](../../MCP.md).
