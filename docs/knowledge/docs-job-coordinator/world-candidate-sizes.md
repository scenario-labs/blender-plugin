---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.world-candidate-sizes",
  "title": "World candidate size reads on the preview lane",
  "description": "The preview-lane command that reads saved World candidates' declared sizes.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "world-candidate-sizes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed on 2026-10-13: JobWorkers.world_sizes enqueues JobCoordinator.world_sizes on the dedicated preview lane, which runs ResultCommands.world_sizes and raises PreviewCanceled when canceled or ResultError once the coordinator is inactive. It validates 1 to the preview scheduler's BATCH_LIMIT (32) (request ID, asset ID, receipt SHA-256) targets before any read, so one check holds the lane no longer than a preview batch, reads each record under the store guard and, for a record in a preview state that still holds that receipt as a World candidate, reads at most the first WORLD_HEADER_BYTES (the 2 MiB preview layout bound) through the regular-file open used for uploads, returning result_previews.local_image_size or None. It does not hash, copy, fetch, transition or claim, and takes no cache root. Offline unit tests cover PNG, JPEG and OpenEXR sizes, stale or ineligible targets, unreadable and far headers, validation, cancellation and the ScenarioPreview lane. This topic covers only the seventh preview lane command and its paragraph; the other preview lane claims keep their own evidence. Review follow-up on 2026-10-13: the bound was 128 targets; it now reuses preview_scheduler.BATCH_LIMIT, imported when the command runs because the scheduler imports the workers that import results.py, and a unit test reads a full batch. preview_scheduler.py joins the sources for that constant; fingerprints of the files this follow-up edits were refreshed.",
    "sources": {
      "scenario/core/jobs/results.py": "63e4366d5e94439406650cced8e311900be385b17b65bc1c0780e1cd38f0171f",
      "scenario/core/jobs/coordinator.py": "fb1fb04d0a474b9fabf3bd6f1dcdc716c07f0e29e409997f8817053912d36c72",
      "scenario/core/jobs/workers.py": "ef94b6776f240f438b26f6af8e9101095674d5f69ba63491d9534deb2949502d",
      "scenario/core/jobs/result_previews.py": "e09571c39571b0cb67268aa98a24f371cb5e1144bc46e10288fe117b485ab779",
      "tests/unit/test_world_sizes.py": "03aa0ef595e70ee0d0c7f0e7cb2d4feb4fa1d6ea9195eafa11bda7896de80c63",
      "scenario/core/jobs/preview_scheduler.py": "6843f4454f32f8fc9f0f1cfa60740fe6d418e52833aa37af32396a8028351295"
    }
  }
}
---

# World candidate size reads on the preview lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
