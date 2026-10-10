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
    "limits": "Reviewed the saved-upload view drawing, the restart action condition, its refresh by the maintenance pump only while the view drew within the last two seconds (a closed view stops the recovery-plan read) and the confirmation dialog with installed native tests on macOS arm64 Blender 5.1.2. No screenshot, focus, keyboard or desktop interaction evidence was collected. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/reference_form.py": "722a0bfae67f7b833e515603dfc0fd77fce8dd26f028f98a33780dc6691fee42",
      "scenario/blender/reference_uploads.py": "bbc2b4f5e8a50bef31694d8764953d21b9b4c45b0f9cf3139f15dbf2a6e3c10f",
      "tests/blender/test_reference_form.py": "c7d13142ee0828cca695e8f1e5a06e0e58f9d186960cc079de3fb83f5acf04f7"
    }
  }
}
---

# Upload again in the saved-upload view

Evidence for [the canonical document](../../UI_STYLE.md).
