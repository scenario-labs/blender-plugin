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
    "limits": "Reviewed that the preview controller runs on Blender's main thread from its own persistent timer, requests still renditions only, answers decode_requests with finish_decode or discard_decode one per tick, builds icons from rehashed cache files, binds tiles to the context token and session, and is retired by RuntimeState.retire_jobs, load_pre and unregister; that background Blender registers no timer; and that the temporary decode leaves a captured scene origin current after a view layer update. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents.",
    "sources": {
      "scenario/blender/result_previews.py": "f3de3c68e2e7d8401775fe27e3fa3f7e5e4e6ef07cb78dab32e11d3aaeab2641",
      "scenario/core/jobs/result_previews.py": "176794d01ab7df94fa49089b3fd566f4d493fd79f7c26f557dff61f8f7102de7",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "969bd75231ed09bc81d32d27089405b47281cfe98391907d6769623d3350af8c",
      "tests/blender/test_result_preview_tiles.py": "be11193504d7053c384b96dce8249b5296cb955ef72bbfd02e194060dc1d85d8",
      "tests/unit/test_result_previews.py": "967eb2e4e0626ef34c1a1a95821e91bc877880463de4c74ba523892dd2c5d050",
      "scenario/blender/runtime.py": "ed7c47498c849441926d2d3032aac00a6b20744e1e8ad75a7f31ca044ab57db2",
      "scenario/blender/registry.py": "108d37f802a97b7ac87753484bd2b3109b306e6cb2810b737ca6c65df9f3ba27",
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Preview controller ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
