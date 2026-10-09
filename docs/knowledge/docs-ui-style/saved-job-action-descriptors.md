---
{
  "type": "Evidence",
  "id": "docs-ui-style.saved-job-action-descriptors",
  "title": "Saved-job controls from shared descriptors",
  "description": "UI rule that saved-job controls come from one descriptor list.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "saved-job-action-descriptors",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that the sidebar Jobs and Generations panels and the Studio Jobs and Results pages draw saved-job controls only through job_recovery.draw_controls, which draws saved_job_actions descriptors; offered actions are drawn enabled and unoffered actions are absent; each operator keeps any confirmation or destination dialog of its own; a shared view without a saved revision draws nothing. Installed Blender 5.1.2 tests on macOS arm64 cover identical view objects across sidebar and Studio pages and ordered descriptor drawing. The rule is policy for later surfaces; no compact composer strip, desktop interaction or screenshot is claimed.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "scenario/blender/job_recovery.py": "2c818c79b349569b164179e3fab91c3b66c056a7054fc86d5b82813b2c171a23",
      "scenario/blender/panels.py": "59b7efd2ee247a3b5d788aaf26e17e32abdc97e8966438287bcb31101a49f935",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "tests/blender/test_result_actions.py": "acd63c3ea3b79cb6a01a5395f14ff83ec6613bf9ec4ad6b0c5cfac9a4d3b29af",
      "tests/blender/test_studio_view.py": "46a6636f4ee0c52919d636905a29510f849b97a0b993885a210c0e1c04e6d6e3"
    }
  }
}
---

# Saved-job controls from shared descriptors

Evidence for [the canonical document](../../UI_STYLE.md).
