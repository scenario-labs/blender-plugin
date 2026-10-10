---
{
  "type": "Evidence",
  "id": "docs-ui-style.workflow-review-previews",
  "title": "Native previews of workflow review assets",
  "description": "Load previews on a waiting step's Jobs row and Studio Workflows entry, and loaded icons in those rows and the review dialog, decoded only by the pump.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "workflow-review-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Load previews paragraph of the Waiting workflow steps section and its installed-test sentences against review_previews.draw_step_previews (one Load previews (N) control per waiting step that lists assets and has a sendable node ID, bound to the context, saved revision, node ID and review_id; up to eight loaded icons, four to a row; ready, loading, waiting for Online Access and unavailable counts; Retry previews while some are unavailable or untracked), job_recovery.draw_controls and workflow_steps.draw_pending (sidebar Jobs, Studio Jobs and Studio Workflows), the dialog's approval grid and candidate icons with status lines and the load hint, its popup refresh only while previews load, SCENARIO_OT_load_workflow_step_previews (network poll, one entry through runtime.load_review_previews, refusals reported), ReviewPreviews.pump decoding at most two stills per tick and never while drawing or while a render job runs, and the pump's redraw on change. Installed tests on the packaged ZIP (macOS arm64 Blender 5.1.2, synthetic SDK responses, offline downloader) cover these controls and their RNA property types, drawing with storage reads, owner creation, requests and decodes refused, decoding only in the pump and not during a render job, the dialog refresh, unavailable candidates and their explicit retry, stale, foreign and offline refusal, released icons after a decision or retirement and cached reuse after a restart. Background Blender assigns no icon IDs, so drawn icons were recorded with a stand-in ID. No screenshot, physical input, focus, DPI, IME or real popup evidence was collected, and no live request was made.",
    "sources": {
      "scenario/blender/workflow_steps.py": "c5d2802629e3173250a96eed972d6282333b8ad0789ffc2d816d42364510a670",
      "scenario/blender/review_previews.py": "508f3a424412cc7b95a9d78870b9c765d3b8c3ee2eeb44ddc010cd193d451bba",
      "scenario/blender/job_recovery.py": "425f54316c84067f910f15a1873a7d5175a372e4cf357bca517966cdcc6a5d8e",
      "scenario/blender/runtime.py": "cf15f250833f0e8afd880ce59c902e5a0924fe38ba1ae527d10f2d5a9417565b",
      "scenario/blender/pump.py": "80e487b5d4aa0b872a741d62793fd5ed78eb281516063aba2ba470803e909f74",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/blender/model_jobs.py": "646ef59978fa1ca97709c36e9884506dd58d45cc2a03cc772d6446aaf146986d",
      "scenario/core/jobs/workflow_nodes.py": "8f073ded509b0eb9bc9f7e2eeb5f61fe08eb1b43f4c4d7d80c7227d00501add4",
      "tests/blender/test_workflow_review_previews.py": "4f8100b75a020836378862af5375d04f86b21cf37ba2220553c3525767157452",
      "tests/blender/test_workflow_steps.py": "77cdf3ee05fc38f0a99de909b751a50bb6188af72938a339efa0b9bf27baf189",
      "tests/blender/test_workflow_commands.py": "1c24de554b5e34efdb2ff060f1091c5a77776d8b5eee3856e86f2dc30632a086"
    }
  }
}
---

# Native previews of workflow review assets

Evidence for [the canonical document](../../UI_STYLE.md).
