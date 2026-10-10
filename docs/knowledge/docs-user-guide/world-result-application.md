---
{
  "type": "Evidence",
  "id": "docs-user-guide.world-result-application",
  "title": "Saved panorama World approval and restoration",
  "description": "Shared native and MCP commands for explicit World application and guarded restoration.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "world-result-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected saved-result World application and restoration through the same native/MCP approval handles, receipt verification, captured scene/current-World guard, durable claim and receipt-only retry. Synthetic tests cover unchanged service request counts, changed destinations, invalid image dimensions, edited World preservation and separate restore approval. The exact ZIP is tested on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop confirms packing, separate mouse approvals, restoration, keyboard/viewport interaction, clean exit and unchanged normal profile. UI_STYLE.md records exact ZIP and test app identity qualification. Only ready/apply_failed saved PNG, JPEG or OpenEXR results (image/png, image/jpeg, image/exr, image/x-exr or image/aces) qualify; application rejects a container that differs from the saved media type, and the native dialog and MCP format field state that declared format. JPEG/ACES offers, the format text, dialog invoke/draw/cancel and local failures with retry state are covered by headless native tests; the 5.1.2 desktop capture predates them. Every new dialog line stays within the 59 characters verified in that capture; desktop interaction with the new wording remains a follow-up under #98. Automatically imported/applied images cannot be reused through this job claim. Session-local restore is not global undo or restart persistence. No new API contract, cloud panorama preset, actual HDR range, seam/pole quality, paid provider acceptance, other OS desktop proof, #263 resolution, full #98 completion or release acceptance. The guide's statements on refused or conflicting EXR color declarations, decoded color space agreement, rejected EXIF-rotated JPEGs and ignored JPEG ICC profiles were reviewed against the panorama-formats evidence for WORLD_APPLICATION.md. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: JobSession adds verified_result, which consumes one verification for an approved destination without an application claim; existing application, receipt and World methods are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/world_application.py": "341b67665ec8be9201c3191559d47a31421aae5726bc2ea06b134f8245876895",
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      "scenario/blender/job_session.py": "fc196b52049308278d50e25f9208edcbef3a872b9398f02af50b12dfe8e76ff2",
      "scenario/blender/model_jobs.py": "7e9fd50f0fff4c0607a62099a64c93d3e94ba3fda04e1c64886b7eb3d37f593e",
      "scenario/blender/runtime.py": "43003d6a75ea5b11f2459ba56d39db94d43359a1cd1564765a10471d7979889e",
      "scenario/blender/job_recovery.py": "a58038f156137b6a0507443c9dade17092364c78c7d538ef7290c9e94908ebbf",
      "scenario/mcp/tools_scenario.py": "29d00c5f120eaa9be1eed7c40e5d5aee0be63c77ee468418cdd8deb9b289a02c",
      "tests/blender/test_model_generation.py": "b873205c0dd69883403c5a0d02e33834f23053eb99489cc9c7193eb39f3ffa61",
      "tests/blender/test_world_application.py": "572c71ac8ea086606fe07c1a2ca3c839ba3b03bc840f6eeed8dc1c8714f9834c",
      "tests/blender/test_session_results.py": "e87afd949fda187702ddac63c0c52f2597fead62c171e2f2afcc9ab217defcf8",
      "tests/unit/test_panorama.py": "f8914ce8c3cbbe10812bed813b3e1fbe1551c71fc6e4f47f8517cb777e9f3fa7",
      "docs/images/saved-world-approval.png": "84efcb774621c15e72798d45cffb74eb307831b7ccdc12ed6169198526604b65",
      "docs/images/saved-world-restore.png": "8c831fb5e0ad0a37735b3760a83a80a8b122b04452768fd166147dce6410c406"
    }
  }
}
---

# Saved panorama World approval and restoration

Evidence for [the canonical document](../../USER_GUIDE.md).
