---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.automatic-result-previews",
  "title": "Preview controller ownership",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the preview controller runs on Blender's main thread from its own persistent timer, requests still renditions only, answers decode_requests with finish_decode or discard_decode one per tick, builds icons from rehashed cache files, binds tiles to the context token and session, and is retired by RuntimeState.retire_jobs, load_pre and unregister; that background Blender registers no timer; and that the temporary decode leaves a captured scene origin current after a view layer update. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed.",
    "sources": {
      "scenario/blender/result_previews.py": "b7b67af43f0be12d483c7211d67b07bff74fb6393a0e0d9aba5bbbd95281b867",
      "scenario/core/jobs/result_previews.py": "176794d01ab7df94fa49089b3fd566f4d493fd79f7c26f557dff61f8f7102de7",
      "scenario/core/jobs/results.py": "5a32f47329d5c71653429b682b8f7e662218b2319b5cfcad7ffe0a46eb8bd6fa",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "tests/blender/test_result_preview_tiles.py": "1e49d3bc815fbec5108860fc645b8d0ef355dadc11d53f01d132663bf4ec98be",
      "tests/unit/test_result_previews.py": "0ddb83960e3d86bd8d691785dc8f239cd4951961716cb859c3006fa6d479b2fe",
      "scenario/blender/runtime.py": "ed7c47498c849441926d2d3032aac00a6b20744e1e8ad75a7f31ca044ab57db2",
      "scenario/blender/registry.py": "108d37f802a97b7ac87753484bd2b3109b306e6cb2810b737ca6c65df9f3ba27",
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47"
    }
  }
}
---

# Preview controller ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
