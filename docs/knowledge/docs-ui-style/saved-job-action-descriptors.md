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
    "base_revision": "c70c7d1bdba93cf29ce5488fa7d83e92f24596b2",
    "limits": "Reviewed that the sidebar Jobs and Generations panels and the Studio Jobs and Results pages draw saved-job controls only through job_recovery.draw_controls, which draws saved_job_actions descriptors; offered actions are drawn enabled and unoffered actions are absent; each operator keeps any confirmation or destination dialog of its own; a shared view without a saved revision draws nothing. Installed Blender 5.1.2 tests on macOS arm64 cover identical view objects across sidebar and Studio pages and ordered descriptor drawing. The rule is policy for later surfaces; no compact composer strip, desktop interaction or screenshot is claimed.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/panels.py": "ffff10ed5d252fca10c6da56156b5e364e0300cbdf88914120d7274d268402f8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "tests/blender/test_result_actions.py": "a0a8de36ed944f1d934c21cd595f773640ea5357f8afa50a7fac9d8e79e8f913",
      "tests/blender/test_studio_view.py": "e6f0fdbdc8aa81bb51880ba4a01da299f54d106babb4e1380216f9d575aed5f7"
    }
  }
}
---

# Saved-job controls from shared descriptors

Evidence for [the canonical document](../../UI_STYLE.md).
