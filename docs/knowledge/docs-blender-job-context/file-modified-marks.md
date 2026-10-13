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
    "base_revision": "df2fac37c5e605854718811ffaf74384d8341033",
    "limits": "Reviewed that the file-modified undo push after a Scenario change leaves captured origins current, and that a first-frame binding without a desktop step still marks the file. Other origin, delivery and history claims retain their separate evidence. Installed evidence: the 54 tests in tests/blender/test_file_modified.py pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Against the main branch's call paths with only the unwired helper present, 27 of the first 38 fail; against earlier heads, 8 review tests for refusals, unchanged state and part-way failures fail, then the title-only workflow reload and the subframe-only frame change. The full installed suite passes on 5.1.2 (1983 tests, 3 Windows-only skips). Blender 5.0 reports every background file as modified, so its runs check the recorded marks and pushes. No desktop quit prompt, live stroke deferral, GUI timer context or Linux/Windows run is recorded here; CI runs the helper and scene-tool classes in the baseline.",
    "sources": {
      "scenario/blender/file_state.py": "899f1eb5423a4d366a7a491a22c8ca08beec4cb83a2b48422abf29ff4de48739",
      "scenario/blender/job_session.py": "1e4715d6a590a15684cfdf8fa956963b26889d6b147c9c745264e06557448138",
      "scenario/blender/first_frame_handoff.py": "3d931d0a3dcaec027577a94408ccea0a090f7e41c6a89ff589ffeb514f365caf",
      "tests/blender/test_file_modified.py": "0712f8a7d2b0a4685d624348f399819beb9d21865a3668e488df2288ff7336bf"
    }
  }
}
---

# File-modified marks keep origins

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
