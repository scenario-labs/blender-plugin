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
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Load previews paragraph of the Waiting workflow steps section and its installed-test sentences against review_previews.draw_step_previews (one Load previews (N) control per waiting step that lists assets and has a sendable node ID, bound to the context, saved revision, node ID and review_id; up to eight loaded icons, four to a row; ready, loading, waiting for Online Access and unavailable counts; Retry previews while some are unavailable or untracked), job_recovery.draw_controls and workflow_steps.draw_pending (sidebar Jobs, Studio Jobs and Studio Workflows), the dialog's approval grid and candidate icons with status lines and the load hint, its popup refresh only while previews load, SCENARIO_OT_load_workflow_step_previews (network poll, one entry through runtime.load_review_previews, refusals reported), ReviewPreviews.pump decoding at most two stills per tick and never while drawing or while a render job runs, and the pump's redraw on change. Installed tests on the packaged ZIP (macOS arm64 Blender 5.1.2, synthetic SDK responses, offline downloader) cover these controls and their RNA property types, drawing with storage reads, owner creation, requests and decodes refused, decoding only in the pump and not during a render job, the dialog refresh, unavailable candidates and their explicit retry, stale, foreign and offline refusal, released icons after a decision or retirement and cached reuse after a restart. Background Blender assigns no icon IDs, so drawn icons were recorded with a stand-in ID. No screenshot, physical input, focus, DPI, IME or real popup evidence was collected, and no live request was made. Re-reviewed on 2026-10-10 after two review preview fixes: the Load previews paragraph now says Retry previews sends unavailable stills through the preview lane again, which fetches a still that failed, is missing or lost its cached file, that decoding uses temporary Blender data so the open file gains no image and captured origins stay current, and that a cached still lost before decoding is fetched again once by itself; the installed-test sentence names the new origin, automatic refetch and Retry cases. Checked against review_previews.py, preview_decode.py, added as a source, and the installed review preview tests; only the touched fingerprints were refreshed. Physical desktop evidence is still pending. Re-checked on 2026-10-10 after restacking on the parents' step-link commits and #384's later head: the dialog's approval section now starts with the parents' unread-links warning when links_complete is false, above the result list and its previews; approvals with a readable workflow definition list, and so preview, their upstream results; and preview_decode's added path refusals raise the same PreviewDecodeError. The preview claims here are unchanged; only the drifted fingerprints of workflow_steps.py, model_jobs.py, workflow_nodes.py, preview_decode.py, tests/blender/test_workflow_steps.py and tests/blender/test_workflow_commands.py were refreshed. Re-reviewed on 2026-10-12 after two review fixes: the installed-test sentence now names a candidate asset listed twice fetched once and an icon Blender could not fill released. Checked against ModelJobs.review_assets, which returns distinct IDs while Load previews (N) and the counts still count candidates, ReviewPreviews._decode and the installed review preview tests. Re-checked on the same day after restacking on the parent's fix that titles an unsupported selection without its range: it changes only workflow_steps.step_title and its test, not the preview drawing, dialog previews or load operator. The other claims are unchanged; only the fingerprints of review_previews.py, model_jobs.py, workflow_steps.py, tests/blender/test_workflow_review_previews.py and tests/blender/test_workflow_steps.py were refreshed.",
    "sources": {
      "scenario/blender/workflow_steps.py": "99b00e703c3c9c599cc9c19edf8bcde1eeaa98e52b8bdc441e28bd7576dea57a",
      "scenario/blender/review_previews.py": "8d304d9dfdcf13c034e7a383510c0397cf93814bb667becdb8c8a7e062bcd9e9",
      "scenario/blender/job_recovery.py": "425f54316c84067f910f15a1873a7d5175a372e4cf357bca517966cdcc6a5d8e",
      "scenario/blender/runtime.py": "cf15f250833f0e8afd880ce59c902e5a0924fe38ba1ae527d10f2d5a9417565b",
      "scenario/blender/pump.py": "80e487b5d4aa0b872a741d62793fd5ed78eb281516063aba2ba470803e909f74",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/blender/model_jobs.py": "5948ae1eb9904b39963685791557d25c091530b8b291afe5a6039459a5aa40ba",
      "scenario/core/jobs/workflow_nodes.py": "ed3b7769ac9ad2195bc5a32febf00b1abbd5df027d059a3e9c45918aa0f6ec7a",
      "tests/blender/test_workflow_review_previews.py": "24be1e483ea81e8b7a0acbf314d49f131f394cae4aead8f381ccfa1c7526e5d8",
      "tests/blender/test_workflow_steps.py": "ec9171401f6b91c9445116df275a3db82a05554e74ab75e61d7010279382e5ae",
      "tests/blender/test_workflow_commands.py": "4b87a0d90615c8808f8688ab0a08b493ac27a81020668c75ff5b5bc6ad2873ec",
      "scenario/blender/preview_decode.py": "e4e201cc9202e4008cfff17f8b5377a62169120359c5517b1907a23fd87d7eef"
    }
  }
}
---

# Native previews of workflow review assets

Evidence for [the canonical document](../../UI_STYLE.md).
