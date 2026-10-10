---
{
  "type": "Evidence",
  "id": "docs-user-guide.remote-progress-projection",
  "title": "Jobs panel progress wording",
  "description": "User-facing description of shared job status words and progress.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed the Jobs bullet against panels.SHARED_STATUS_TEXT, SHARED_OFFLINE_TEXT, progress.LABELS and the percent rule, the two-second POLL_INTERVAL with redraw on row or online access change, the stale and offline line texts and restart behaviour that needs the Refresh status or Resume download descriptor labels. ModelJobs gives a SUCCEEDED view whose results it downloads (downloads_results) a non-terminal display status, so a finished generation stays in Jobs as finished on Scenario, then downloading results and, as non-terminal ready, results saved until applied; the Image lane's automatic import ends in applied, which Generations lists. With online access off the finished row shows Download paused while online access is disabled; an installed test draws that row through the real Jobs panel and shows the download resuming once access returns. Finished Prompt Spark, Translate and Blockout records keep the terminal succeeded; installed tests inspect each with Inspect saved jobs and find it listed only in Generations. The ready row staying in Jobs until a non-Image result is applied is established by code review of JobRecord.is_terminal and the display mapping. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. Scoped 2026-10-12 check of the Render Video first-frame handoff, not a full re-review: ModelJobs adds the use_first_frame action, its single-use approval, the verify_first_frame command and the session-local first_frame status field; polling, delivery predicates, progress projection, bindings and other actions are unchanged. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-12 check of the native first-frame control, not a full re-review: ModelJobs.poll also writes first_frame_assets, the eligible still asset IDs, into each saved view's meta for the native descriptor; saved_job_actions now describes use_first_frame as a per-asset control and no longer skips it; status words, progress, delivery, offline lines and redraws are unchanged. The claims above still hold; the review date and base revision are unchanged. On 2026-10-12 the model_jobs.py, saved_job_actions.py and helpers.py fingerprints were refreshed after the saved model package import was rebuilt on this topic's sources. It adds import-unit projection, status fields, per-format import controls and package journeys beside the unchanged progress projection: view.meta import_units is set before _project_remote, and status adds import_units, import_findings and model_import beside lane and the remote fields. The Refresh status and Resume download descriptor labels are unchanged, and a ready model job still stays in Jobs until an import applies it. These claims were rechecked and the review date is unchanged. On 2026-10-12 the model_jobs.py, saved_job_actions.py and helpers.py fingerprints were refreshed again after saved splat import was stacked on the package import. It adds splat approval options, worker preparation and import notices to model_jobs.py, with view.meta import_notices set before _project_remote, splat options to the MCP tools, splat labels and notice rows to the descriptors and splat fixtures to the tests. The explicit splat preparation discards a pending automatic application like any explicit import, so the progress projection and delivery predicates are unchanged. The Refresh status and Resume download labels are unchanged. These claims were rechecked and the review date is unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason through the shared _refusal wording. This topic's statements were rechecked against that change and are unchanged; only the fingerprints of the sources that change touched were refreshed, other drift is left as it was, and the review date is unchanged. A scoped re-inspection for the compact composer job strip found that model_jobs.py only gains the read-only busy and imports_automatically accessors that the composer's job strip reads; the projection, reading, binding and drawing claims are unchanged. The review date and earlier evidence are unchanged.",
    "sources": {
      "scenario/blender/panels.py": "6865424bb96bd545a60a72ae5fad6531eccc97016fdd8eac21857d29eecf5415",
      "scenario/blender/model_jobs.py": "2f1d9b1f4dfd70898c47590a8b55c76af8f60e2377692e36c85138a4a3187377",
      "scenario/blender/pump.py": "d146e694610b8ec4ca23b4577da1d792d4ae2c0dbc8d7a8a88d690571a330acd",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "tests/blender/test_model_generation.py": "505d6e569450a339535038db01c26484550a6bfd0bc0c1dffb1d35d207da8df9",
      "tests/blender/helpers.py": "d3a77292bc65b1421a98c470ed3c0ba531eeb5e2d83dc1c2fb2c11b426703f73",
      "tests/blender/test_prompt_tools.py": "a9c04c117248f0630d8a9f02af2df95357904fae5ae767e260a97d0531d9a10b",
      "tests/blender/test_blockout_jobs.py": "94a8e8157b551e2604229b3d5a57df0e9a74b8572476fbd527a077b4ff8a4069"
    }
  }
}
---

# Jobs panel progress wording

Evidence for [the canonical document](../../USER_GUIDE.md).
