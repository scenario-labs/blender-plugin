---
{
  "type": "Evidence",
  "id": "docs-mesh-application.windowless-model-import",
  "title": "Windowless static model import",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "windowless-model-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "ea77f3a542be698301bd0a414579d4a9e40650bb",
    "limits": "Inspected the optional window context in receipt-bound staged import. Static GLBs retain explicit scene/view-layer import and saved remesh application without a window; actual skins require a window before importer execution. The exact packaged ZIP passed 711 native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Regressions check selection, active object, rollback, temporary cleanup and rig rejection. Ordinary supported background sessions retain an off-screen window, so background execution alone does not imply this condition. No UI behavior, SDK call or dependency change; desktop input, live-provider and release acceptance remain separate.",
    "sources": {
      "scenario/blender/model_application.py": "6c42d9daf48a998f09aafd8d10e42f35a076e4bca81458f23e65df594ebf39a8",
      "scenario/blender/mesh_result_application.py": "8541b1f4f68e9eddb519f25bb8f27954722fd09b51623bfe20de06a66fa95be5",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "tests/blender/test_model_application.py": "dc3d79aeb59fd9037b9f9a5e41c92ddf789a2b17b30ea0de76e133883cd6c134",
      "tests/blender/test_mesh_result_application.py": "dce8a32090541da9866b06c01e217ee786bc93c45a92126c90685cbc766cf04f"
    }
  }
}
---

# Windowless static model import

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
