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
    "limits": "Reviewed the saved-upload view drawing, the restart action condition and the confirmation dialog with installed native tests on macOS arm64 Blender 5.1.2. No screenshot, focus, keyboard or desktop interaction evidence was collected. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/reference_form.py": "989a59fb5468988957a212725951643d43887d4bcdf116d65784bf0ce3613041",
      "scenario/blender/reference_uploads.py": "0d78fa5712d1740df1d91698b87fb4a6ea4c482768ec249520b84db9826926d5",
      "tests/blender/test_reference_form.py": "73ccd343f9ddc28d50074ec287e9b449637deea9d6506949bc754efb347ab585"
    }
  }
}
---

# Upload again in the saved-upload view

Evidence for [the canonical document](../../UI_STYLE.md).
