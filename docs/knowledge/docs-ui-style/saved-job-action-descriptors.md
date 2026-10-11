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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that the sidebar Jobs and Generations panels and the Studio Jobs and Results pages draw saved-job controls only through job_recovery.draw_controls, which draws saved_job_actions descriptors; offered actions are drawn enabled and unoffered actions are absent; each operator keeps any confirmation or destination dialog of its own; a shared view without a saved revision draws nothing. Installed Blender 5.1.2 tests on macOS arm64 cover identical view objects across sidebar and Studio pages and ordered descriptor drawing. The rule is policy for later surfaces; no compact composer strip, desktop interaction or screenshot is claimed. Re-checked on main after #370: panels.py and studio.py drift adds the derived history row kind and the Film review page and leaves saved-job drawing on draw_controls; a freshly inspected saved remote job draws no Cancel generation until a refresh confirms an inference job, consistent with hiding an action that is not offered. test_result_actions now runs in the PR baseline.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/panels.py": "c47a4301db4e2383c240dc2bde3dc86fd1d7a910a43c2da4a02dad235e0539b3",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "tests/blender/test_result_actions.py": "f9ef9207e0052aba850d165dfdefc05a09b2894fd59e8cb4d5c0e8172a65c1ad",
      "tests/blender/test_runtime_jobs.py": "9cbc0a763541264ae1c3f291a7754c09755066f60dc11f03206ba1fe8f398cf3",
      "tests/blender/test_studio_view.py": "d65762fbbcf6ce9dd63356097697c30b9b22a8fb07bec0866c3ae64e79ad8c7c",
      "tests/blender/run_all.py": "5fa3f8c12ade901f48a21021eba62e61cb80f8e2edac569f67c4f1c54960f195"
    }
  }
}
---

# Saved-job controls from shared descriptors

Evidence for [the canonical document](../../UI_STYLE.md).
