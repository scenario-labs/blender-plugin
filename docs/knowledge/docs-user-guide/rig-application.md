---
{
  "type": "Evidence",
  "id": "docs-user-guide.rig-application",
  "title": "Compatible rig attachment",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "rig-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected explicit saved-result RIG policy, exact geometry/weight validation, captured-source preservation, retained rig hierarchy/clips, synchronous rollback, UI/MCP approval, native undo and receipt-only recovery. Exact ZIP passed 715 installed tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop cancellation, attachment, undo/redo, selection and timeline skin deformation verified with synthetic transport. Completed repeat exited cleanly with unchanged normal profile; earlier interrupted exit crashed in fixture temporary-preference finalization. No existing-rig retargeting, provider compatibility, other OS desktop or integrated release acceptance. Other evidence retains its separate scope.",
    "sources": {
      "scenario/blender/rig_application.py": "7ea6dfbb1d6d87cd78128b57013d1643997f4864bfa97883fc1be1c45c430031",
      "scenario/blender/mesh_application.py": "02a55e41868b98f9f01a7ac355e4123479eea2c5503a0ecc27a2846c9819cfb2",
      "scenario/blender/mesh_result_application.py": "89da3577ce7621bf1ba37df744dbf952b8b247a9b4d6d90c8846532d67d19887",
      "scenario/blender/job_recovery.py": "8ba455f6cb177bd0c1b7dda20ccbeda912a1bdbefb19271de3a95e32c61f11c6",
      "scenario/blender/model_jobs.py": "e0bb958978c44f702697dea5374e9a20e47af2e9bf77bc91a3f9b64db15e3b01",
      "scenario/mcp/tools_scenario.py": "5163560ee3f04039c567d02007d425f10333b7314c76ec533dc6810e380db817",
      "tests/blender/helpers.py": "e5f6937be429c970101f5a12b54e2188ba03772af6805211e9bf9dc98cd928a9",
      "tests/blender/test_mesh_result_application.py": "c9e1fb7bf71b25e9950b3db5636a5f888168fadd22e890faff21adaa69589b2a",
      "tests/blender/test_model_generation.py": "59d244a4f6c8d0a0f0b0c3a07d65329dc373555cbe0be5fed0cbd2fb3b723921",
      "docs/images/saved-mesh-rig-approval.png": "208b563dfa130cd702ba5a1af4a1d02c3dd0925e133f6a92dc2d7f9974f7953b",
      "docs/images/saved-mesh-rig-animated.png": "9d710a319adb61c0ab1867a54f68eb95aa69109772fbd96ff5c533721bb450c8"
    }
  }
}
---

# Compatible rig attachment

Evidence for [the canonical guide](../../USER_GUIDE.md).
