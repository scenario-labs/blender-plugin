---
{
  "type": "Evidence",
  "id": "docs-user-guide.upload-restart",
  "title": "Upload again for an unfinished reference upload",
  "description": "Native saved-upload recovery restarts an upload that cannot continue.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "upload-restart",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Inspect uploads view, its Upload again confirmation and the shared facade restart. Installed native tests on macOS arm64 Blender 5.1.2 cover the offered action, the confirmation call, the restarted upload reaching imported and explicit attachment with Use this reference. No GUI interaction, desktop screenshot, Blender 5.0/5.2 run, multipart file above one part or media kind other than PNG image was exercised live. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/reference_form.py": "989a59fb5468988957a212725951643d43887d4bcdf116d65784bf0ce3613041",
      "scenario/blender/reference_uploads.py": "0d78fa5712d1740df1d91698b87fb4a6ea4c482768ec249520b84db9826926d5",
      "scenario/core/jobs/uploads.py": "4b6220ed463bd8b2e2be62a7fb1b567929161f36233c396efd005690cc6ac3dc",
      "tests/blender/test_reference_form.py": "73ccd343f9ddc28d50074ec287e9b449637deea9d6506949bc754efb347ab585",
      "tests/blender/test_reference_uploads.py": "7b3ddfa61ba562200e7258f53bd372d7782608e05cf977a466db1b86e28c109b"
    }
  }
}
---

# Upload again for an unfinished reference upload

Evidence for [the canonical document](../../USER_GUIDE.md).
