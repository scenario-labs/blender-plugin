---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.remote-progress-projection",
  "title": "Shared job progress projection and redraw",
  "description": "Runtime map entry for the progress projection, binding and pump redraw.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed that context maintenance projects the validated remote reading and records the display-only scene lane binding in ModelJobs, that MCP job_status reads the same view projection, and that pump._jobs_changed compares drawn job rows (excluding transient offered actions) and online access and redraws only when they change, in addition to existing event redraws; pump.redraw tags the 3D viewport and Preferences regions. Restarted views stay generic and unbound. Installed tests cover one redraw per projected change and per online access change, and none on idle ticks or for a queued refresh. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. Scoped 2026-10-12 check of the Render Video first-frame handoff, not a full re-review: ModelJobs adds the use_first_frame action, its single-use approval, the verify_first_frame command and the session-local first_frame status field; polling, delivery predicates, progress projection, bindings and other actions are unchanged; tools_scenario adds the video_first_frame purpose and description text for it, job_status first_frame, render_form source_result and first_frame_route, and refusal of described exclusive file inputs in raw generate bodies; other contracts are unchanged. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-12 check of the native first-frame control, not a full re-review: ModelJobs.poll also writes first_frame_assets, the eligible still asset IDs, into each saved view's meta for the native descriptor; status words, progress, delivery, offline lines and redraws are unchanged. The claims above still hold; the review date and base revision are unchanged. On 2026-10-12 the model_jobs.py and tools_scenario.py fingerprints were refreshed after the saved model package import was rebuilt on this topic's sources. It adds import-unit projection, status fields, per-format import controls and package journeys beside the unchanged progress projection: view.meta import_units is set before _project_remote, and status adds import_units, import_findings and model_import beside lane and the remote fields. Context maintenance, the MCP job_status reading and pump._jobs_changed are unchanged; these claims were rechecked and the review date is unchanged. On 2026-10-12 the model_jobs.py and tools_scenario.py fingerprints were refreshed again after saved splat import was stacked on the package import. It adds splat approval options, worker preparation and import notices to model_jobs.py, with view.meta import_notices set before _project_remote, splat options to the MCP tools, splat labels and notice rows to the descriptors and splat fixtures to the tests. The explicit splat preparation discards a pending automatic application like any explicit import, so the progress projection and delivery predicates are unchanged. These claims were rechecked and the review date is unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason through the shared _refusal wording. This topic's statements were rechecked against that change and are unchanged; only the fingerprints of the sources that change touched were refreshed, other drift is left as it was, and the review date is unchanged. A scoped re-inspection for the compact composer job strip found that model_jobs.py only gains the read-only busy and imports_automatically accessors that the composer's job strip reads; the projection, reading, binding and drawing claims are unchanged. The review date and earlier evidence are unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "2f1d9b1f4dfd70898c47590a8b55c76af8f60e2377692e36c85138a4a3187377",
      "scenario/blender/pump.py": "d146e694610b8ec4ca23b4577da1d792d4ae2c0dbc8d7a8a88d690571a330acd",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/mcp/tools_scenario.py": "4c29c000a9064231adfc58412c0246305366ecf021366230969b853cfc45f625",
      "tests/blender/test_model_generation.py": "505d6e569450a339535038db01c26484550a6bfd0bc0c1dffb1d35d207da8df9"
    }
  }
}
---

# Shared job progress projection and redraw

Evidence for [the canonical document](../../architecture/runtime.md).
