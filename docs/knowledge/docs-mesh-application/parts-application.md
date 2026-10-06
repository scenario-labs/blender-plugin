---
{
  "type": "Evidence",
  "id": "docs-mesh-application.parts-application",
  "title": "Static parts application",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "parts-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "e4da254583900a68da7414e0ac2744656831e47f",
    "limits": "Inspected explicit static PARTS saved-GLB application, empty source anchor, named child copies, mapping, Keep original, bounded input, rollback, shared UI/MCP and native undo/redo. Exact ZIP passed 699 native tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop cancellation, captured-source confirmation, history, Outliner and viewport input verified with synthetic transport. No live provider semantic classification/alignment, rig/animation, other-platform desktop or integrated release acceptance. Existing evidence retains its separate scope. The mesh-error follow-up ZIP b5e207c2bd571e89e31e45e1dce24a43fd341ba1f23766bc2792e4be6445eb9c passed 700 native tests each on the same three versions; its isolated 5.1.2 desktop verified full error text, preserved source/selection and viewport input without new service work. Earlier desktop screenshots remain tied to their preceding artifact.",
    "sources": {
      "scenario/blender/mesh_result_application.py": "8541b1f4f68e9eddb519f25bb8f27954722fd09b51623bfe20de06a66fa95be5",
      "scenario/blender/mesh_application.py": "b575b30cd254950e367420669584977cb00126e944b2abc698de2283b05e03e3",
      "scenario/blender/model_jobs.py": "a010e0806ed27823e492c951c142f5ca8ea2dc1f83e238d3f642bcdc649db127",
      "scenario/blender/job_recovery.py": "36dac65be6e9012985153777d34faea618d00d2001fdb34a2b80bd668c82a117",
      "scenario/mcp/tools_scenario.py": "c3033950c92186e06b61ea47bc296c77b0ddd90dc33cc91b5b8d954292e5b35c",
      "tests/blender/helpers.py": "40a372edd8d529df3ff1878389de7bad28998d81bf09add32217e5d5441daee3",
      "tests/blender/test_mesh_result_application.py": "e54cb80540c795d8d65855d1b14015538da749230d65c15b636bad69c4c61c08",
      "tests/blender/test_model_generation.py": "0410b57c051b27f4fbef91dbf904380b426a4c493c1dbd4dd5a8be6a8cd442b0",
      "docs/images/saved-mesh-parts-approval.png": "54eb80c296f57deca90ba7972c82cd3cc38aff747c5d532e3fa902fe38ab8f5c",
      "docs/images/saved-mesh-parts-applied.png": "200363db61458746c7f9aa390e2b6bcb11bd85d18db86ff58c6adcf5909ae913"
    }
  }
}
---

# Static parts application

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
