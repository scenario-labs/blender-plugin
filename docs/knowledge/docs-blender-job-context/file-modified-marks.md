---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.file-modified-marks",
  "title": "File-modified marks keep origins",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "file-modified-marks",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed that the file-modified undo push after a Scenario change leaves captured origins current, and that a first-frame binding without a desktop step still marks the file. Other origin, delivery and history claims retain their separate evidence. Installed evidence: the 38 tests in tests/blender/test_file_modified.py pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, and 27 of them fail against the main branch's call paths with only the unwired helper present. The full installed suite passes on 5.1.2 (1899 tests, 3 Windows-only skips). Blender 5.0 reports every background file as modified, so its runs check the recorded marks and pushes. No desktop quit prompt, live stroke deferral, GUI timer context or Linux/Windows run is recorded here; CI runs the helper and scene-tool classes in the baseline.",
    "sources": {
      "scenario/blender/file_state.py": "2ba4b6bfddf80e63f22572d1c1e0396b2b10ae2180611cd35940e6b9d5dd63a1",
      "scenario/blender/job_session.py": "885978a987115b692a23a507bc9282b902a4c182c84b87e8c6e0bf65ed782831",
      "scenario/blender/first_frame_handoff.py": "3d931d0a3dcaec027577a94408ccea0a090f7e41c6a89ff589ffeb514f365caf",
      "tests/blender/test_file_modified.py": "2e83f3219c5f424ce7d9f7b0504e466cb60c2db0485bed05590e6d61a6021e79"
    }
  }
}
---

# File-modified marks keep origins

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
