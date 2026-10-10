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
    "limits": "Reviewed the Inspect uploads view, its Upload again confirmation and the shared facade restart. Installed native tests on macOS arm64 Blender 5.1.2 cover the offered action, including after a transfer stops while the view is open, the confirmation call, the restarted upload reaching imported and explicit attachment with Use this reference. No GUI interaction, desktop screenshot, Blender 5.0/5.2 run, multipart file above one part or media kind other than PNG image was exercised live. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/reference_form.py": "722a0bfae67f7b833e515603dfc0fd77fce8dd26f028f98a33780dc6691fee42",
      "scenario/blender/reference_uploads.py": "bbc2b4f5e8a50bef31694d8764953d21b9b4c45b0f9cf3139f15dbf2a6e3c10f",
      "scenario/core/jobs/uploads.py": "06cacc568478204ddbbba7f67f03d48da85fe492a8db8dcf04df14db35944aef",
      "tests/blender/test_reference_form.py": "c7d13142ee0828cca695e8f1e5a06e0e58f9d186960cc079de3fb83f5acf04f7",
      "tests/blender/test_reference_uploads.py": "7b3ddfa61ba562200e7258f53bd372d7782608e05cf977a466db1b86e28c109b"
    }
  }
}
---

# Upload again for an unfinished reference upload

Evidence for [the canonical document](../../USER_GUIDE.md).
