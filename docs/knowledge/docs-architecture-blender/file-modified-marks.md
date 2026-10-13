---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.file-modified-marks",
  "title": "Marking the file modified",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "file-modified-marks",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Inspected every local MCP tool and main-thread application path for Blender data changes outside an Undo operator, and the shared file_state helper they now call: one ed.undo_push per completed change, the first window when the context has none, deferral during sculpt, paint and paint-curve strokes until the next pump tick, a dropped mark on file read, and no second step after saved model, mesh or first-frame checkpoints. Blender 5.1.2 source (ED_undo_push, ED_OT_undo_push, timer context) reviewed; pushes tag no ID and run no dependency or history handler, checked against a captured session origin. Installed evidence: the 38 tests in tests/blender/test_file_modified.py pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, and 27 of them fail against the main branch's call paths with only the unwired helper present. The full installed suite passes on 5.1.2 (1899 tests, 3 Windows-only skips). Blender 5.0 reports every background file as modified, so its runs check the recorded marks and pushes. No desktop quit prompt, live stroke deferral, GUI timer context or Linux/Windows run is recorded here; CI runs the helper and scene-tool classes in the baseline.",
    "sources": {
      "scenario/blender/file_state.py": "2ba4b6bfddf80e63f22572d1c1e0396b2b10ae2180611cd35940e6b9d5dd63a1",
      "scenario/blender/job_session.py": "885978a987115b692a23a507bc9282b902a4c182c84b87e8c6e0bf65ed782831",
      "scenario/blender/model_jobs.py": "3c59cc3a4958a2780a9bb9cda414c8860e16a5bc27ddb4908448c08b85510e95",
      "scenario/blender/first_frame_handoff.py": "3d931d0a3dcaec027577a94408ccea0a090f7e41c6a89ff589ffeb514f365caf",
      "scenario/blender/prompt_jobs.py": "c2ff180e68b6586f87d41475963d057b24a41b7c54cc6a439ed1d3ca9714d6b4",
      "scenario/blender/blockout_jobs.py": "45f847d5d0269d453bd284c8494be70aefb405264089d9f09ee42187ecabb5c2",
      "scenario/blender/workflow_controls.py": "36aaaf19575d27ebd80c109363b8bc7535b301a2eca7d284b49a0d50df4cf1a4",
      "scenario/blender/reference_form.py": "e3828f6fa358e31c45c316e6452e542ca717a7eef646865f4aba6c3f2b4e0df5",
      "scenario/blender/workflow_uploads.py": "39fc4d14f4617c0e27ab0ee27676e5adf537b4dfff2d379ba2666e1afe2cc692",
      "scenario/blender/film.py": "e03d6cd281184ac147f80c8f6beaaae429d7e4c3d0f7f02c1afcfb860e16cb0d",
      "scenario/blender/pump.py": "d9c855f4e5b13bdafd31b9120439c811979261393b44f4c96a775bb50ff8b77b",
      "scenario/blender/registry.py": "c6cebfa2d7ff1e026c7bc609674def56dfec738c2f50d282797121b094457907",
      "scenario/mcp/tools_blender.py": "17be31e1d9f12afe06720a77562d632394fef529127137a85d8cddf3b58b8740",
      "scenario/mcp/tools_scenario.py": "cd49a8d45f5008001cff45f7ba2829f672cb24d6cd8c516028b99ef987794a39",
      "tests/blender/test_file_modified.py": "2e83f3219c5f424ce7d9f7b0504e466cb60c2db0485bed05590e6d61a6021e79",
      "tests/blender/helpers.py": "d1fe2a0d2f92597a112a9e18d46c3d9ea5fa705b48b59d44ece356cd4bb884eb",
      "tests/blender/run_all.py": "fc75f9cacccf0200cd05eece6605bd358afc8740a03c09cf56c0a2080af60dc9",
      "scenario/blender/generation.py": "5de665107c0cb70a8f1fb0adaf8bd4a36026e64a935b3f6d615f9d003f0ccafb",
      "scenario/blender/params_ui.py": "c41d76277605de313226da7696b700617c67f2c63b013af552cc4fd1d0feb78b"
    }
  }
}
---

# Marking the file modified

Evidence for [the canonical guide](../../architecture/blender.md).
