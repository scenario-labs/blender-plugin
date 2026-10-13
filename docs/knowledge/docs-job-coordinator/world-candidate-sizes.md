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
    "base_revision": "0d266fa3c1397402686a841f8e979c0a1db9a0ca",
    "limits": "Reviewed on 2026-10-13: JobWorkers.world_sizes enqueues JobCoordinator.world_sizes on the dedicated preview lane, which runs ResultCommands.world_sizes and raises PreviewCanceled when canceled or ResultError once the coordinator is inactive. It validates 1 to 128 (request ID, asset ID, receipt SHA-256) targets before any read, reads each record under the store guard and, for a record in a preview state that still holds that receipt as a World candidate, reads at most the first WORLD_HEADER_BYTES (the 2 MiB preview layout bound) through the regular-file open used for uploads, returning result_previews.local_image_size or None. It does not hash, copy, fetch, transition or claim, and takes no cache root. Offline unit tests cover PNG, JPEG and OpenEXR sizes, stale or ineligible targets, unreadable and far headers, validation, cancellation and the ScenarioPreview lane. This topic covers only the seventh preview lane command and its paragraph; the other preview lane claims keep their own evidence.",
    "sources": {
      "scenario/core/jobs/results.py": "42d3da86d0e5b1e746b22f8abd3d7cd5d2f5b1444d4c9afeb9da4c9dc1b95b0a",
      "scenario/core/jobs/coordinator.py": "fb1fb04d0a474b9fabf3bd6f1dcdc716c07f0e29e409997f8817053912d36c72",
      "scenario/core/jobs/workers.py": "ef94b6776f240f438b26f6af8e9101095674d5f69ba63491d9534deb2949502d",
      "scenario/core/jobs/result_previews.py": "e09571c39571b0cb67268aa98a24f371cb5e1144bc46e10288fe117b485ab779",
      "tests/unit/test_world_sizes.py": "df099b3954a2c357574ac8641e9fe116ae0027173facfd94a204867b06647880"
    }
  }
}
---

# World candidate size reads on the preview lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
