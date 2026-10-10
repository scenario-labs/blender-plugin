---
{
  "type": "Evidence",
  "id": "docs-ui-style.compact-job-strip",
  "title": "Compact job strip",
  "description": "UI rules for the composer's current-job tray, its chips and job card.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "compact-job-strip",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed composer_geometry, strip_job, strip_spec, overlap_vertical_insets and _draw_strip in draw.py; _geometry, _invoke, _still_drawn, _job_click and _job_dismiss in modal.py; the dismissed, drawn_strips and offered caches and shown_actions in state.py; SCENARIO_OT_composer_job_card and draw_job in job_card.py; registration and _load_pre in the composer package; and the job_strip and composer_layout strip helpers they call. The strip shows the newest ModelJobs.bound_views entry for the scene session_uid and the lane ComposerState.shown_form returns, unless dismissed; strip_status receives the saved state, the projected reading's status, fraction and stale flag, the view error, imports_automatically, membership in submissions as in_flight and runtime.online; chips come from strip_chips over job_recovery.result_actions. job_strip now takes its active remote words from core.jobs.progress.LABELS, capitalized (pending reads Waiting, finalizing reads Finishing); its percent rule (1 to 99, in-progress only) still differs from the Jobs bar, which also shows finalizing and 0 or 100 percent. strip_placement gets the layout's side insets and header, tool header and asset shelf heights measured from visible overlapping regions. Drawing writes only state.layout and the composer's Python caches. The modal hit-tests the same geometry, compares the drawn signature before dispatch, flushes a focused prompt with flush_focused_prompt, refuses an action it only holds while ModelJobs.busy, and calls bpy.ops with INVOKE_DEFAULT only. The job card looks up the view in ModelJobs.views, then jobs_view, draws draw_active_job or draw_result(collapsible=False) and registers its popup with studio.track_popup for the pump's redraw_popups. Unit tests cover the strip wording table and the Jobs panel word alignment. Installed native tests (tests/blender/test_composer_jobs.py) ran on the packaged ZIP on Blender 5.1.2 macOS arm64 only, over jobs submitted through the synthetic SDK transport of test_model_generation: the real draw handler with recording primitives, the real modal handler with synthetic events, and the real recover_job operator for Resume download. Dialogs and the job card popup opened from inside the composer modal were recorded, not shown; no desktop interaction, screenshot, alternate UI scale, Blender 5.0/5.2 run, other operating system or live provider job is claimed, and that acceptance stays under #66 and #68.",
    "sources": {
      "scenario/blender/composer/draw.py": "c620b16740877ed1094839e4b9d44961b3cfe8d7730d0ccc87ee6f55f0524132",
      "scenario/blender/composer/modal.py": "dd3b5895468ec5489da840dae6af42d8c5cf1c717049c9db675cc27114e3ca5d",
      "scenario/blender/composer/state.py": "6c270ea079c7743f2961187e1f293084ce34aed3e83f8a7fff57022f7534ec92",
      "scenario/blender/composer/job_card.py": "cf7f0c9deec08067b0368da1e425932bb03b766ee5f0080721f2b56328747809",
      "scenario/blender/composer/__init__.py": "b930c2585cbe825af6cfaf0b0a9acf4daa55a78e90297325be4911b1a2cb6449",
      "scenario/core/ui/job_strip.py": "5c5c08c72a9842192b89bb9006158ac6f7b0234c3ca92bc4af33ffc2c51380bc",
      "scenario/core/ui/composer_layout.py": "cca5f608aeb8648ec8ee91de5d38dcbccbd08f280818cfde7bd703afb12da592",
      "tests/blender/test_composer_jobs.py": "e87bf43716455803acc5ed7d15445654877cdac6789f1c170466f455bb3e2117",
      "tests/unit/test_job_strip.py": "c89a08d5dbb4b52df1fe0b8d811744e85e7070fd32fc644a98d00bc08afebe39",
      "scenario/blender/model_jobs.py": "51c6d13d89c99345b1c597adefae08a60e64d0eb985c0eaf0ee6bfd29361c50f",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "scenario/blender/panels.py": "ad434c1ef11225ae17a3d612d43aec0692ffe3df7dc07483da03fbe8048f7e9c",
      "scenario/blender/studio.py": "4621e12d9c807a14b8ecea38c1d6cf16373526167a3fb37daf5d853f3182350c",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "tests/unit/test_composer_strip_layout.py": "0177c88e553b47c3440849604ef440fac9cf9e244d60421737b44643387b972c"
    }
  }
}
---

# Compact job strip

Evidence for [the canonical document](../../UI_STYLE.md#compact-job-strip).
