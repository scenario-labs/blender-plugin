---
{
  "type": "Evidence",
  "id": "docs-ui-style.upload-restart",
  "title": "Upload again in the saved-upload view",
  "description": "Restart is offered only for uploads whose suggested recovery is a restart, behind a confirmation.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "upload-restart",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the saved-upload view drawing, the restart action condition, its refresh by the maintenance pump while the view is open and the confirmation dialog with installed native tests on macOS arm64 Blender 5.1.2. No screenshot, focus, keyboard or desktop interaction evidence was collected. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/reference_form.py": "989a59fb5468988957a212725951643d43887d4bcdf116d65784bf0ce3613041",
      "scenario/blender/reference_uploads.py": "baf59355688ad53ae084291e9860554fe305d71a7d1bb3ca01af66d73b5ef6cd",
      "tests/blender/test_reference_form.py": "57ff5a04242c37bf8e5651710d9cb6f5f2c0d806daded365c3a0034282ad4a3a"
    }
  }
}
---

# Upload again in the saved-upload view

Evidence for [the canonical document](../../UI_STYLE.md).
