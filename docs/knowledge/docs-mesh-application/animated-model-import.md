---
{
  "type": "Evidence",
  "id": "docs-mesh-application.animated-model-import",
  "title": "Rigged and animated model import",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "animated-model-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected bounded embedded GLB import into a new group, rig/weights/morph/clip retention, scene timing, window and optional glTF UI restoration, rollback and shared UI/MCP approval. Placement measures the first clip at frame zero in the staging scene before publication, independent of destination time; native regression compares two nonzero import frames, approved cursor placement and retained motion. Earlier exact-ZIP desktop cancellation, confirmation, viewport/Outliner input and timeline evidence remains bounded to the artifact recorded in UI_STYLE.md. No new desktop acceptance is claimed by this placement fix. No in-place rig/animation transfer, new-group global undo, live provider, other OS desktop or integrated release acceptance. Other evidence retains its separate scope. On 2026-10-10 staged_model's staging moved into a shared _stage helper without a GLB behavior change, and the saved-job command now reaches the same GLB importer through the package snapshot path, with its preflight before the claim. These claims and the review date are unchanged. On 2026-10-10 the model_application.py fingerprint was refreshed after saved splat import added the splat summary field, the worker format sets and docstring lines; the GLB animation path is unchanged, and the review date is unchanged. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date.",
    "sources": {
      "scenario/blender/job_recovery.py": "ebd918cbcaaa26987ad50f046cd6e83f9133684736233ef122dfcc544d0d092e",
      "scenario/blender/model_application.py": "ede45e886635fcb3768673ba83c0ee7e5b99d59ed2f8fc9a8d537028b9832dc9",
      "scenario/blender/model_jobs.py": "9bd00cd64350304705ec32e227c307d39bf83bfdaf4353d6d435c05d9f562e34",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/mcp/tools_scenario.py": "6cac2cbf6e0b5ed7a21ed8eaedbfaa4b03f212e99185f8b4a63ea3ae44062893",
      "tests/blender/helpers.py": "5f058cf46d2eb672444a5eef2b019aae0935ea92e14d5462c684c20bcff57a6c",
      "tests/blender/test_mesh_result_application.py": "1da2d9c30f4e43d2f9b49a8e85670051365960b87cdffa6f523c335b26b7c0dc",
      "tests/blender/test_model_application.py": "21d0ff0623f68951f3eb2e6edda73c2d5aa35b0917c8b333e512d056648e0802",
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

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
