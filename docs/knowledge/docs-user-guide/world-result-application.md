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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected saved-result World application and restoration through the same native/MCP approval handles, receipt verification, captured scene/current-World guard, durable claim and receipt-only retry. Synthetic tests cover unchanged service request counts, changed destinations, invalid image dimensions, edited World preservation and separate restore approval. The exact ZIP is tested on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop confirms packing, separate mouse approvals, restoration, keyboard/viewport interaction, clean exit and unchanged normal profile. UI_STYLE.md records exact ZIP and test app identity qualification. Only ready/apply_failed saved PNG, JPEG or OpenEXR results (image/png, image/jpeg, image/exr, image/x-exr or image/aces) qualify; application rejects a container that differs from the saved media type, and the native dialog and MCP format field state that declared format. JPEG/ACES offers, the format text, dialog invoke/draw/cancel and local failures with retry state are covered by headless native tests; the 5.1.2 desktop capture predates them. Every new dialog line stays within the 59 characters verified in that capture; desktop interaction with the new wording remains a follow-up under #98. Automatically imported/applied images cannot be reused through this job claim. Session-local restore is not global undo or restart persistence. No new API contract, cloud panorama preset, actual HDR range, seam/pole quality, paid provider acceptance, other OS desktop proof, #263 resolution, full #98 completion or release acceptance. The guide's statements on refused or conflicting EXR color declarations, decoded color space agreement, rejected EXIF-rotated JPEGs and ignored JPEG ICC profiles were reviewed against the panorama-formats evidence for WORLD_APPLICATION.md.",
    "sources": {
      "scenario/blender/world_application.py": "341b67665ec8be9201c3191559d47a31421aae5726bc2ea06b134f8245876895",
      "scenario/core/scene/panorama.py": "a66306a9c8d82c14d2f299fa26a62468d4db7f852111b3bfcb47f434e5e2aa63",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "scenario/blender/model_jobs.py": "7e9fd50f0fff4c0607a62099a64c93d3e94ba3fda04e1c64886b7eb3d37f593e",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/blender/job_recovery.py": "a58038f156137b6a0507443c9dade17092364c78c7d538ef7290c9e94908ebbf",
      "scenario/mcp/tools_scenario.py": "29d00c5f120eaa9be1eed7c40e5d5aee0be63c77ee468418cdd8deb9b289a02c",
      "tests/blender/test_model_generation.py": "b873205c0dd69883403c5a0d02e33834f23053eb99489cc9c7193eb39f3ffa61",
      "tests/blender/test_world_application.py": "dff1d3a7308e303a67f21225f29e7e403074015ef4d384e66e364a926bee7395",
      "tests/blender/test_session_results.py": "e87afd949fda187702ddac63c0c52f2597fead62c171e2f2afcc9ab217defcf8",
      "tests/unit/test_panorama.py": "a5716070211c058ef1b7eff39b38da789de8a0a32782e478a8910d2df404f678",
      "docs/images/saved-world-approval.png": "84efcb774621c15e72798d45cffb74eb307831b7ccdc12ed6169198526604b65",
      "docs/images/saved-world-restore.png": "8c831fb5e0ad0a37735b3760a83a80a8b122b04452768fd166147dce6410c406"
    }
  }
}
---

# Saved panorama World approval and restoration

Evidence for [the canonical document](../../USER_GUIDE.md).
