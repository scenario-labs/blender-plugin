---
{
  "type": "Evidence",
  "id": "tests-smoke-readme",
  "title": "tests/smoke/README.md evidence",
  "evidence": {
    "path": "tests/smoke/README.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-18",
    "reviewed_revision": "04c30c3b7815ff8983a59c0e37a05608db23455e",
    "limits": "Source-reviewed against the smoke tools, the shared panorama contract and the workflow. No live quote, upload, paid generation, hosted or scheduled run, or Blender report run; provider acceptance of the committed monthly plan and reference image is not established.",
    "sources": [
      ".github/workflows/smoke.yml",
      "scenario/core/jobs/result_metadata.py",
      "scenario/core/jobs/results.py",
      "scenario/core/jobs/upload_sources.py",
      "scenario/core/jobs/upload_store.py",
      "scenario/core/jobs/upload_transfers.py",
      "scenario/core/jobs/uploads.py",
      "scenario/core/scene/panorama.py",
      "scenario/core/scene/panorama_contract.py",
      "tests/blender/test_panorama_report.py",
      "tests/fixtures/models/model_google-gemini-3-1-flash.json",
      "tests/fixtures/models/model_patina-material.json",
      "tests/fixtures/synthetic/reference-toadstool-512.png",
      "tests/smoke/monthly-plan.json",
      "tests/smoke/smoke_image.py",
      "tests/smoke/smoke_image_to_3d.py",
      "tests/smoke/smoke_material.py",
      "tests/smoke/smoke_video.py",
      "tests/unit/test_panorama.py",
      "tests/unit/test_panorama_report.py",
      "tests/unit/test_reference_fixture.py",
      "tests/unit/test_smoke_ci.py",
      "tests/unit/test_smoke_image.py",
      "tests/unit/test_smoke_inputs.py",
      "tests/unit/test_smoke_monthly.py",
      "tests/unit/test_smoke_panorama.py",
      "tests/unit/test_smoke_suite.py",
      "tools/blender_env.py",
      "tools/panorama_report.py",
      "tools/smoke_ci.py",
      "tools/smoke_image.py",
      "tools/smoke_inputs.py",
      "tools/smoke_model.py",
      "tools/smoke_suite.py"
    ]
  }
}
---

Evidence for [the canonical document](../../tests/smoke/README.md).
