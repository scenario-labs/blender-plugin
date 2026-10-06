---
{
  "type": "Evidence",
  "id": "docs-user-guide.animated-model-import",
  "title": "Rigged and animated model import",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "animated-model-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected bounded embedded GLB import into a new group, rig/weights/morph/clip retention, scene timing, window and optional glTF UI restoration, rollback and shared UI/MCP approval. Exact ZIP passed 705 installed tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop cancellation, confirmation, viewport/Outliner input and animated timeline scrubbing verified with synthetic transport. Completed repeat exited cleanly with unchanged normal profile; prior interrupted fixture shutdown crashed in temporary-preference cleanup. No in-place rig/animation transfer, new-group global undo, live provider, other OS desktop or integrated release acceptance. Other evidence retains its separate scope.",
    "sources": {
      "scenario/blender/job_recovery.py": "ebd918cbcaaa26987ad50f046cd6e83f9133684736233ef122dfcc544d0d092e",
      "scenario/blender/model_application.py": "ae730d74dacc8fee03fe31401e125e4ae3d2c1c5622364d5ba6669433c9d2cf0",
      "scenario/blender/model_jobs.py": "9bd00cd64350304705ec32e227c307d39bf83bfdaf4353d6d435c05d9f562e34",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/mcp/tools_scenario.py": "6cac2cbf6e0b5ed7a21ed8eaedbfaa4b03f212e99185f8b4a63ea3ae44062893",
      "tests/blender/helpers.py": "19a32d58d34efc0322fc60e08be2e3cb0416c2b9a26bb6bf829a44c8eeab4940",
      "tests/blender/test_mesh_result_application.py": "1da2d9c30f4e43d2f9b49a8e85670051365960b87cdffa6f523c335b26b7c0dc",
      "tests/blender/test_model_application.py": "8e2b2e414f8c64914a6a9af284518f937e20036ec0550bff9e39ec04d7bd453c",
      "tests/blender/test_model_generation.py": "9c3062ea7713163bd8fa75e7b0568a0f1302ab8241428c2a96932b08b1dd4ccd",
      "tests/unit/test_glb.py": "361bd8095611ec198c7f8af6329aaaa5475fa074fe67cb71038759a813f3f626",
      "docs/images/saved-model-animation-start.png": "3cb6e3843751c3ca2abd9923416f4a1f8fe2e9059c1e392cd7850a8a28342ff1",
      "docs/images/saved-model-animation-approval.png": "979ebfbb766cec3b6bc01dd7316a65cae885697914e4f21243b088be540d7126",
      "docs/images/saved-model-animation-end.png": "c87c4e7b2a3d66c38662394fb87e3ad6609d570d6729775d81cbfdbe31bcf61f"
    }
  }
}
---

# Rigged and animated model import

Evidence for [the canonical guide](../../USER_GUIDE.md).
