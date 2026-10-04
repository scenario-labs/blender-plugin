---
{
  "type": "Evidence",
  "id": "docs-ui-style.parts-application",
  "title": "Static parts application",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "parts-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected explicit static PARTS saved-GLB application, empty source anchor, named child copies, mapping, Keep original, bounded input, rollback, shared UI/MCP and native undo/redo. Exact ZIP passed 699 native tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop cancellation, captured-source confirmation, history, Outliner and viewport input verified with synthetic transport. No live provider semantic classification/alignment, rig/animation, other-platform desktop or integrated release acceptance. Existing evidence retains its separate scope.",
    "sources": {
      "scenario/blender/mesh_result_application.py": "8541b1f4f68e9eddb519f25bb8f27954722fd09b51623bfe20de06a66fa95be5",
      "scenario/blender/mesh_application.py": "b575b30cd254950e367420669584977cb00126e944b2abc698de2283b05e03e3",
      "scenario/blender/model_jobs.py": "81b619f7a5c541234e0e92508640585e3b02cd785e7b9097ea56c3c9c86cab8a",
      "scenario/blender/job_recovery.py": "36dac65be6e9012985153777d34faea618d00d2001fdb34a2b80bd668c82a117",
      "scenario/mcp/tools_scenario.py": "c3033950c92186e06b61ea47bc296c77b0ddd90dc33cc91b5b8d954292e5b35c",
      "tests/blender/helpers.py": "40a372edd8d529df3ff1878389de7bad28998d81bf09add32217e5d5441daee3",
      "tests/blender/test_mesh_result_application.py": "e54cb80540c795d8d65855d1b14015538da749230d65c15b636bad69c4c61c08",
      "tests/blender/test_model_generation.py": "ddcdb2fb9e51b5369fddaf6548c4013cf32612d4de23b724944c6f32f9bc9456",
      "docs/images/saved-mesh-parts-approval.png": "54eb80c296f57deca90ba7972c82cd3cc38aff747c5d532e3fa902fe38ab8f5c",
      "docs/images/saved-mesh-parts-applied.png": "200363db61458746c7f9aa390e2b6bcb11bd85d18db86ff58c6adcf5909ae913"
    }
  }
}
---

# Static parts application

Evidence for [the canonical guide](../../UI_STYLE.md).
