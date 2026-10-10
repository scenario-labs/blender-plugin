---
{
  "type": "Evidence",
  "id": "docs-result-previews.result-previews",
  "title": "Receipt-bound saved-result previews",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the bpy-free preview module, owner-thread scheduler, coordinator and result commands, the workers' dedicated preview lane and its idleness, the adapter's bulk asset reads, the downloader's cancellation event, still header dimension parsing, the audio envelope math and the JobSession/runtime wiring, including the new polling window a later requested rendition opens, also when it overtakes a final poll already on the lane, cache and work paths built on the canonical root, eviction that counts only bytes actually removed so an undeletable entry leaves the next oldest in line, a maintenance-only lane command that evicts after writes once no batch is due, server preview transfer failures, including a redirect to another host through the real downloader over a mocked connection, that stay pending within the window and fail at its end while receipt and content failures fail at once, and a session that runs without previews when its cache root cannot be created. Unit tests use the real SDK with MockTransport, a host-policy-enforcing offline downloader and synthetic media headers; Windows' extended-namespace root is modeled in unit tests by respelling POSIX roots; native tests ran the installed ZIP on Blender 5.1.2 (macOS arm64) only, so Windows native behavior rests on hosted CI, not on this review. No live SDK metadata, CDN transfer or redirect, thumbnail coverage, dimensions, timing or size evidence; no Blender-side decoding, UI, MCP or desktop acceptance. No store schema change.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "d33234f02a85f67a573ca1d097ebd8921578ba3c38047811249ac4484367c7d3",
      "scenario/core/jobs/preview_scheduler.py": "bfe2b96bad5f175a28ca71b95d6cc0d478e40ee009e55c7929724fca88898a65",
      "scenario/core/jobs/results.py": "217d9c40dddffd5cb109313e62b27d6055526b7cbb4032eb1292ef2c6d04b92e",
      "scenario/core/jobs/coordinator.py": "79c7c4aeaa4e0d9dfb9047ffcc1f5101330a7fda36ec81e8f450d8d9d072e883",
      "scenario/core/jobs/workers.py": "08f9d8488e9df9892177a2f2570422d5d3e3a35dae89796f469640d4e2b97f35",
      "scenario/core/api/sdk_adapter.py": "258e4fba314e2c1ac030ff65a9e63b4c0bf88c5f89e5eea4217ca0f36303b9fc",
      "scenario/core/audio_waveform.py": "bca1b2b029aded0da993a52093d0f0e49b016c82ee777a7fe4713a8473efda3e",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/blender/job_session.py": "a47e759441bddfd645e1dd17626600dc3c81d1e0938488619d31c69f11f804d2",
      "scenario/blender/runtime.py": "aa199b156270fbc86aa6dbc5edf30096dddac7e69de6cc1ea905d5619b2a51bb",
      "tests/unit/test_result_previews.py": "937a378d1aa27ff7e9aa1ff2f086521bd62fd52d26227297029febe3d75a1fbd",
      "tests/unit/test_preview_scheduler.py": "b7aa9552994cb02a6dfabcabd24c1a1e187f6bc9bafbe9411ad859782e83376b",
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
