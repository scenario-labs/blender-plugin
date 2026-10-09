---
{
  "type": "Evidence",
  "id": "docs-result-previews.result-previews",
  "title": "Receipt-bound saved-result previews",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the bpy-free preview module, owner-thread scheduler, coordinator and result commands, the workers' dedicated preview lane, the adapter's single and bulk asset reads, the audio envelope math and the JobSession/runtime wiring. Unit tests use the real SDK with MockTransport, a host-policy-enforcing offline downloader and synthetic media; native tests ran the installed ZIP on Blender 5.1.2 (macOS arm64) only. No live SDK metadata, CDN transfer, thumbnail coverage, timing or size evidence; no Blender-side decoding, UI, MCP or desktop acceptance. No store schema change.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "c8c8574a201ddbd979126120c0ae872ecaff851a00661b2a12472991a55b9cce",
      "scenario/core/jobs/preview_scheduler.py": "4a8d4924e4e959be28ab314ddce976f5e7290cf461ae8e784475e185da0d28f7",
      "scenario/core/jobs/results.py": "53b3c6b9cea1092b6011f67ac4960c199551c8d0c0aef1c76e5948c4b3401094",
      "scenario/core/jobs/coordinator.py": "6a61a53044ac5dcaa46ccd0c2ff2c672d275b2fbbc4b719d6881f311e69720e9",
      "scenario/core/jobs/workers.py": "ff77957be1e66ca7f24abc04b9378a39ca9f3db7959e00abc326f5fb6b0b2f66",
      "scenario/core/api/sdk_adapter.py": "c224d4ca17565315726553848c9bc9471ea418b52a87c271c9211dfb283ced24",
      "scenario/core/audio_waveform.py": "bca1b2b029aded0da993a52093d0f0e49b016c82ee777a7fe4713a8473efda3e",
      "scenario/core/jobs/transfers.py": "36a1a3d9482bfec2ed79b2205a935198f195591b2ed64f991318dd7a21b2fb3b",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/blender/job_session.py": "a4a5a108a4b500ce09448f027243973a6116f8e615bcc7444902a561741a772d",
      "scenario/blender/runtime.py": "5c7d192dcdc8cbfc0b3e3d13d4e786d8bbaee67b855d6deaad80eaf0b08d746d",
      "tests/unit/test_result_previews.py": "ee00b4a254224b007ce89d6fca50fdf6806ba0381847fe93ee4bcd0b5563aa6c",
      "tests/unit/test_preview_scheduler.py": "983759e1177dcb961d4d3bd057cb2c6281761f75ec9310a31eb3430787c72404",
      "tests/unit/test_audio_envelope.py": "5f51aa5ec09cbfc3283c0ef51cf8833363ce90609029f782de8edd4897ce8bde",
      "tests/unit/test_job_workers.py": "e83d56663d556c583ca16b99c613775a16e916c01128767ab6658d965257aaf3",
      "tests/blender/test_result_previews.py": "bcb6a24461461201d7f3560f87c261f433cb3adf30d111936d815d917be9b7de"
    }
  }
}
---

# Receipt-bound saved-result previews

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
