---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.mesh-edit-approval",
  "title": "Saved mesh edit approval",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "mesh-edit-approval",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected UI/MCP saved-mesh target approval, explicit coordinate/policy options, single-use handles, native operator entry, stale target rejection, separate completed-result reuse and persistence-only recovery. Synthetic installed tests establish local behavior, not provider alignment or pre-generation source export binding. Desktop control timed out; mouse/keyboard/focus/viewport proof remains pending. Other edit policies, global undo, persistent restoration, live service and release acceptance remain incomplete. No new SDK/API operation or paid test. Other topics retain their original scope.",
    "sources": {
      "scenario/blender/model_jobs.py": "0c891b5fcbcb8bad780c1e0731f3f04069507b0ac0548e4d56e89d08d36cfc02",
      "scenario/blender/job_recovery.py": "d14ef853e122fd77ed41712d7950c8c4f83105ddbfec7f757b9a2520d360cc45",
      "scenario/blender/runtime.py": "fad8c3b706e8826740c57c357052099fcad3e6b147e0acc9ee95332ce6ea2fc5",
      "scenario/blender/job_session.py": "5216d7c5b3dae533e653645526f40f2fa4d6d51b1534f5f12912546a042f0a49",
      "scenario/blender/mesh_result_application.py": "73ef54edb7fe04c6c3807db817b35f13655fdb2d57aaf83b622f6fd6a8aee70f",
      "scenario/mcp/tools_scenario.py": "ed2ccd0b21a7a6ac465280493015ee8d99d2ec84881a32c7b7e7b2dbad2a7676",
      "tests/blender/test_model_generation.py": "ffa27c20d89607735c78fb2e6d240668e3ce569cd35f0bcba4dd6d86cefc50bf"
    }
  }
}
---

# Saved mesh edit approval

Evidence for [the canonical guide](../../architecture/runtime.md).
