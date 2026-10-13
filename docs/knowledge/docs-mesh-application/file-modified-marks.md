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
    "base_revision": "df2fac37c5e605854718811ffaf74384d8341033",
    "limits": "Reviewed that a saved mesh edit without desktop checkpoints marks the file modified through the shared session command, and that recorded checkpoints are not followed by another step. Other mesh history claims retain their separate evidence. Installed evidence: the 52 tests in tests/blender/test_file_modified.py pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Against the main branch's call paths with only the unwired helper present, 27 of the first 38 fail; against the previous head, 8 of the review tests for refusals, unchanged state and part-way failures fail. The full installed suite passes on 5.1.2 (1981 tests, 3 Windows-only skips). Blender 5.0 reports every background file as modified, so its runs check the recorded marks and pushes. No desktop quit prompt, live stroke deferral, GUI timer context or Linux/Windows run is recorded here; CI runs the helper and scene-tool classes in the baseline.",
    "sources": {
      "scenario/blender/file_state.py": "899f1eb5423a4d366a7a491a22c8ca08beec4cb83a2b48422abf29ff4de48739",
      "scenario/blender/job_session.py": "1e4715d6a590a15684cfdf8fa956963b26889d6b147c9c745264e06557448138",
      "scenario/blender/mesh_result_application.py": "f873d4900a1f8a8cc86c8d0a729f6ac2b1905cac943ef224cdd4e0e553b3cf3b",
      "tests/blender/test_file_modified.py": "de19155d1a3c15f5a95f7dbd52bad686a9de48989b8333fff8bd060ab028d4a7"
    }
  }
}
---

# Background mesh edits mark the file

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
