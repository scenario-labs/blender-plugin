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
    "limits": "Reviewed that the sidebar Jobs and Generations panels and the Studio Jobs and Results pages draw saved-job controls only through job_recovery.draw_controls, which draws saved_job_actions descriptors; offered actions are drawn enabled and unoffered actions are absent; each operator keeps any confirmation or destination dialog of its own; a shared view without a saved revision draws nothing. Installed Blender 5.1.2 tests on macOS arm64 cover identical view objects across sidebar and Studio pages and ordered descriptor drawing. The rule is policy for later surfaces; no compact composer strip, desktop interaction or screenshot is claimed. Scoped 2026-10-10 check of the native first-frame control, not a full re-review: saved_job_actions no longer has MCP_ONLY and describes use_first_frame as one scenario.use_saved_first_frame control per asset ID that ModelJobs projects in first_frame_assets, numbered over every saved asset, with no operator icon like the other controls; job_recovery registers that operator; the unit vocabulary, MCP purpose parity and installed registered-property tests include it. Other descriptors, their order and the read-only drawing are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "f360aa25c33a2bb37889c559a824357946e5644bf6fe786dd937c5bd4e1ba8de",
      "scenario/blender/job_recovery.py": "012d4a61956de59aa057de3fa2d77c5290e95bccb09519e71de334fad88659ce",
      "scenario/blender/panels.py": "ffff10ed5d252fca10c6da56156b5e364e0300cbdf88914120d7274d268402f8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "tests/blender/test_result_actions.py": "3ce294d7ef49195ac612d99f977571c460c1a0f0eccb992275ad12b6554a52ec",
      "tests/blender/test_studio_view.py": "e6f0fdbdc8aa81bb51880ba4a01da299f54d106babb4e1380216f9d575aed5f7"
    }
  }
}
---

# Saved-job controls from shared descriptors

Evidence for [the canonical document](../../UI_STYLE.md).
