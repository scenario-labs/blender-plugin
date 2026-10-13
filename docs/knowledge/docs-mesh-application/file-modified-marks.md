---
{
  "type": "Evidence",
  "id": "docs-mesh-application.file-modified-marks",
  "title": "Background mesh edits mark the file",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "file-modified-marks",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed that a saved mesh edit without desktop checkpoints marks the file modified through the shared session command, and that recorded checkpoints are not followed by another step. Other mesh history claims retain their separate evidence. Installed evidence: the 38 tests in tests/blender/test_file_modified.py pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, and 27 of them fail against the main branch's call paths with only the unwired helper present. The full installed suite passes on 5.1.2 (1899 tests, 3 Windows-only skips). Blender 5.0 reports every background file as modified, so its runs check the recorded marks and pushes. No desktop quit prompt, live stroke deferral, GUI timer context or Linux/Windows run is recorded here; CI runs the helper and scene-tool classes in the baseline.",
    "sources": {
      "scenario/blender/file_state.py": "2ba4b6bfddf80e63f22572d1c1e0396b2b10ae2180611cd35940e6b9d5dd63a1",
      "scenario/blender/job_session.py": "885978a987115b692a23a507bc9282b902a4c182c84b87e8c6e0bf65ed782831",
      "scenario/blender/mesh_result_application.py": "f873d4900a1f8a8cc86c8d0a729f6ac2b1905cac943ef224cdd4e0e553b3cf3b",
      "tests/blender/test_file_modified.py": "2e83f3219c5f424ce7d9f7b0504e466cb60c2db0485bed05590e6d61a6021e79"
    }
  }
}
---

# Background mesh edits mark the file

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
