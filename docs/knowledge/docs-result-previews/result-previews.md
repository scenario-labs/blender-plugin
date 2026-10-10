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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the bpy-free preview module, owner-thread scheduler, coordinator and result commands, the workers' dedicated preview lane and its idleness, the adapter's bulk asset reads, the downloader's cancellation event, still header dimension parsing, the audio envelope math and the JobSession/runtime wiring, including the new polling window a later requested rendition opens, also when it overtakes a final poll already on the lane, cache and work paths built on the canonical root, and a session that runs without previews when its cache root cannot be created. Unit tests use the real SDK with MockTransport, a host-policy-enforcing offline downloader and synthetic media headers; Windows' extended-namespace root is modeled in unit tests by respelling POSIX roots; native tests ran the installed ZIP on Blender 5.1.2 (macOS arm64) only, so Windows native behavior rests on hosted CI, not on this review. No live SDK metadata, CDN transfer, thumbnail coverage, dimensions, timing or size evidence; no Blender-side decoding, UI, MCP or desktop acceptance. No store schema change.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "792b330dcb9007e9b4500cdca119e8122eb93a1c64e9e9fbcf881a96650c689c",
      "scenario/core/jobs/preview_scheduler.py": "cb75fc5ff870438352430c331ea7a2a4a5d9da307dfb44ad9a44bfbdb2c5e7dc",
      "scenario/core/jobs/results.py": "b914e5d3dd6920d61dbfc93c44f23c65c2bec70c82b8322bfda405c200461341",
      "scenario/core/jobs/coordinator.py": "6a61a53044ac5dcaa46ccd0c2ff2c672d275b2fbbc4b719d6881f311e69720e9",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "scenario/core/api/sdk_adapter.py": "258e4fba314e2c1ac030ff65a9e63b4c0bf88c5f89e5eea4217ca0f36303b9fc",
      "scenario/core/audio_waveform.py": "bca1b2b029aded0da993a52093d0f0e49b016c82ee777a7fe4713a8473efda3e",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/blender/job_session.py": "a47e759441bddfd645e1dd17626600dc3c81d1e0938488619d31c69f11f804d2",
      "scenario/blender/runtime.py": "aa199b156270fbc86aa6dbc5edf30096dddac7e69de6cc1ea905d5619b2a51bb",
      "tests/unit/test_result_previews.py": "076c04df828fe9068be328f754da0c01dc8c3134d1bd2d6065d33ee01971ee0d",
      "tests/unit/test_preview_scheduler.py": "2e5b9b8a67e24ea8afe20c954b8ac6d66092e4ed57a6c0846e357e7e5b9ff463",
      "tests/unit/test_audio_envelope.py": "5f51aa5ec09cbfc3283c0ef51cf8833363ce90609029f782de8edd4897ce8bde",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "tests/blender/test_result_previews.py": "a42261da4a269ef3e91b76f2260eca6d81d17831d51f29fb2c1cb62972e8b2e2",
      "tests/unit/test_result_transfers.py": "2b412aed88b59ed5233a95aedb7bbca69de89b900f694b14205fb18f937fb8af",
      "tests/blender/test_runtime_jobs.py": "56f200b664856a6ac44820ae48f605fc48b59a745733e70cf09d6e89278d29f4"
    }
  }
}
---

# Receipt-bound saved-result previews

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
