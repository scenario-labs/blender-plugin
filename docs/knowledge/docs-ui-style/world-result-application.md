---
{
  "type": "Evidence",
  "id": "docs-ui-style.world-result-application",
  "title": "Saved panorama World approval and restoration",
  "description": "Shared native and MCP commands for explicit World application and guarded restoration.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "world-result-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Inspected saved-result World application and restoration through the same native/MCP approval handles, receipt verification, captured scene/current-World guard, durable claim and receipt-only retry. Synthetic tests cover unchanged service request counts, changed destinations, invalid image dimensions, edited World preservation and separate restore approval. The exact ZIP is tested on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop confirms packing, separate mouse approvals, restoration, keyboard/viewport interaction, clean exit and unchanged normal profile. UI_STYLE.md records exact ZIP and test app identity qualification. Only ready/apply_failed saved PNG/EXR results qualify; automatically imported/applied images cannot be reused through this job claim. Session-local restore is not global undo or restart persistence. No new API contract, cloud panorama preset, actual HDR range, seam/pole quality, paid provider acceptance, other OS desktop proof, #263 resolution, full #98 completion or release acceptance.",
    "sources": {
      "scenario/blender/world_application.py": "95a10cae5b1ec3fdc758a18dcb4e70a50ffe10961c1ab38e0c5bb9ea6dbe8934",
      "scenario/core/scene/panorama.py": "e2d14956bb8240780919ae9f8824afc6bec4e1c62c222d0fe4d10276044f2fa8",
      "scenario/blender/job_session.py": "335de8e165b859f6e475d33b49c535e9772d204ab68616a4f288b7a9700a4c33",
      "scenario/blender/model_jobs.py": "1bd5368ea594cfd9471416f75d42c229c9661c32037d0d1e9dd9d49fef545051",
      "scenario/blender/runtime.py": "9c6cced2f5a40d44b2072cca49694af0b8f7085d91d58db21145acd9cd50201b",
      "scenario/blender/job_recovery.py": "aef8c18aba82400a2dbf4465d7a4a29f2fa612150fef7b20e0ce840aa793ec2f",
      "scenario/mcp/tools_scenario.py": "04974f3aff9539804b6d2d9463900f1bc3397050beb709dbee44149c48fc8796",
      "tests/blender/test_model_generation.py": "70ecc1d2c41cf5c60b82d0cf826158b249f5902f9ddbc48ba679ab8d279d25ad",
      "tests/blender/test_world_application.py": "f8fddd0ddf5d5e4612c9109585f95db64a51d9a3aac4a050d59a7a8b66ba796b",
      "tests/blender/test_session_results.py": "abf066db37b5065da617ecfadb4c718dddba6aa4596382e764495f8185af68b6",
      "tests/unit/test_panorama.py": "f75277778003314b0e7b29a97e8547b3a2ddb1a2dfaf8148a3ab6edd53923950",
      "docs/images/saved-world-approval.png": "84efcb774621c15e72798d45cffb74eb307831b7ccdc12ed6169198526604b65",
      "docs/images/saved-world-restore.png": "8c831fb5e0ad0a37735b3760a83a80a8b122b04452768fd166147dce6410c406"
    }
  }
}
---

# Saved panorama World approval and restoration

Evidence for [the canonical document](../../UI_STYLE.md).
