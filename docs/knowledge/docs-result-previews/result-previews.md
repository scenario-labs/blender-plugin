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
    "limits": "Inspected the bpy-free preview module, owner-thread scheduler, coordinator and result commands, the workers' dedicated preview lane and its idleness, the adapter's bulk asset reads, the downloader's cancellation event, still header dimension parsing, the audio envelope math and the JobSession/runtime wiring, including the new polling window a later requested rendition opens, cache and work paths built on the canonical root, and a session that runs without previews when its cache root cannot be created. Unit tests use the real SDK with MockTransport, a host-policy-enforcing offline downloader and synthetic media headers; Windows' extended-namespace root is modeled in unit tests by respelling POSIX roots; native tests ran the installed ZIP on Blender 5.1.2 (macOS arm64) only, so Windows native behavior rests on hosted CI, not on this review. No live SDK metadata, CDN transfer, thumbnail coverage, dimensions, timing or size evidence; no Blender-side decoding, UI, MCP or desktop acceptance. No store schema change.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "4d7f61239c07d9f4b5f07663011fea3d89439955aa50bda6dcc282faacd64a2c",
      "scenario/core/jobs/preview_scheduler.py": "ba072b0748b5210527ed953da66794a8e3fca3617608960bc8a0a57a42d9737c",
      "scenario/core/jobs/results.py": "b914e5d3dd6920d61dbfc93c44f23c65c2bec70c82b8322bfda405c200461341",
      "scenario/core/jobs/coordinator.py": "6a61a53044ac5dcaa46ccd0c2ff2c672d275b2fbbc4b719d6881f311e69720e9",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "scenario/core/api/sdk_adapter.py": "c224d4ca17565315726553848c9bc9471ea418b52a87c271c9211dfb283ced24",
      "scenario/core/audio_waveform.py": "bca1b2b029aded0da993a52093d0f0e49b016c82ee777a7fe4713a8473efda3e",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/blender/job_session.py": "f8ea693820df79a9e51d103873349f0e5d6512996841f0536dd091b15438757c",
      "scenario/blender/runtime.py": "e7d96070a984d22c589b33c035597fec6f3b2eb53ae28551c3e26b82f6b5ee34",
      "tests/unit/test_result_previews.py": "4fe845288119b74ba49b89d136777ccc5257ccf1f8a690d65f285e612f4fe01a",
      "tests/unit/test_preview_scheduler.py": "fc371a0b47c6036282610f4c6f11feb24770dfb9bd1e44472953255527c815e8",
      "tests/unit/test_audio_envelope.py": "5f51aa5ec09cbfc3283c0ef51cf8833363ce90609029f782de8edd4897ce8bde",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "tests/blender/test_result_previews.py": "a42261da4a269ef3e91b76f2260eca6d81d17831d51f29fb2c1cb62972e8b2e2",
      "tests/unit/test_result_transfers.py": "2b412aed88b59ed5233a95aedb7bbca69de89b900f694b14205fb18f937fb8af",
      "tests/blender/test_runtime_jobs.py": "dc7ad681a477b8f926e35eabde60b9d76f18e86ac97b901473f81abea58582a6"
    }
  }
}
---

# Receipt-bound saved-result previews

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
