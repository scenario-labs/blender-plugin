---
{
  "type": "Evidence",
  "id": "docs-result-previews.result-previews",
  "title": "Receipt-bound saved-result previews",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the bpy-free preview module, owner-thread scheduler, coordinator and result commands, the workers' dedicated preview lane and its idleness, the adapter's bulk asset reads, the downloader's cancellation event, still header dimension parsing, the audio envelope math and the JobSession/runtime wiring, including the new polling window a later requested rendition opens, also when it overtakes a final poll already on the lane, cache and work paths built on the canonical root, eviction that counts only bytes actually removed so an undeletable entry leaves the next oldest in line, a maintenance-only lane command that evicts after writes once no batch is due, a retry that reports its renditions queued at once and withdraws their outstanding decode requests, also behind an in-flight batch whose late ready, missing, failed or offline outcome the same pump replaces with the restart, without changing which settled entries eviction may drop, server preview transfer failures, including a redirect to another host and a response without the Content-Length the downloader requires when no size is expected, through the real downloader over a mocked connection, that stay pending within the window and fail at its end while receipt and content failures fail at once, a session that runs without previews when its cache root cannot be created, and saved image/aces originals, which are not previewed. Unit tests use the real SDK with MockTransport, a host-policy-enforcing offline downloader and synthetic media headers; Windows' extended-namespace root is modeled in unit tests by respelling POSIX roots; native tests ran the installed ZIP on Blender 5.1.2 (macOS arm64) only, so Windows native behavior rests on hosted CI, not on this review. No live SDK metadata, CDN transfer or redirect, thumbnail coverage, dimensions, timing or size evidence; no Blender-side decoding, UI, MCP or desktop acceptance. No store schema change. Re-reviewed on 2026-10-10 for workflow review previews: the introduction now names them as the only user interface, the scheduler interface adds request_review and the review flag of retry and status, and the boundaries add the unverified review sources; those claims are covered by the workflow-review-previews topic. For saved results, preview_scheduler.py (entry keys that also carry the review flag), result_previews.py (shared thumbnail parsing, the review kind and key, review_sources and check_still) and results.py (review targets and their record check) leave the receipt binding, sources, polling, cache and lane behavior described here unchanged, as the unchanged saved-result unit tests show; only the fingerprints of touched sources that matched the base were refreshed. Saved results still have no Blender-side decoding, UI, MCP or desktop acceptance. Rechecked on 2026-10-13 after the shared installed-tool lookup: ffmpeg and ffprobe are now found by scenario/core/jobs/installed_tools.py (PATH first, then fixed macOS and Linux install folders; Windows uses PATH only) in media_probe.probe_tool, local_render.media_tools, local_export verification and film_export.verifier, and tests fake that lookup instead of shutil.which. This topic's claims are unchanged. Only the media_probe.py fingerprint was refreshed; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "b17c9f0ebd80e222090c0ad83339b27d7f261a7e1cb5a7bf02d2ca261d9ceb09",
      "scenario/core/jobs/preview_scheduler.py": "aedd1fa55614dd342688a15bba9639fb31f10590d2bbd7dfd4be2344912641d2",
      "scenario/core/jobs/results.py": "a1c52d70390adcc49900e5ef457e0c0c864e0ecb5cd313ecbc268a43994bbc95",
      "scenario/core/jobs/coordinator.py": "aa0524bec5371d0541829223babd29cdf78f3bbca5231d1de1d5179afff2bd58",
      "scenario/core/jobs/workers.py": "dece4686af0b0889b99341a99d6d5143d48cdf63919fecef90299b834fbe9bc3",
      "scenario/core/api/sdk_adapter.py": "d19509e010e0b04252b948fc035b9096b06151d6360bd76f5939a94a1c407605",
      "scenario/core/audio_waveform.py": "bca1b2b029aded0da993a52093d0f0e49b016c82ee777a7fe4713a8473efda3e",
      "scenario/core/jobs/transfers.py": "af6442afac9d146fab63563a04f62e97440b6eef9099b579a3f2dfe4fcae2e2c",
      "scenario/core/jobs/media_probe.py": "a5a1d357cb51809060c5275f9ddcc2eae7f161c1d8e7ee4cacedd259de80a0e4",
      "scenario/blender/job_session.py": "856baab7ec8aa2786f27ee482b0acc30a8f895fe547664e905b43304ad0ed08a",
      "scenario/blender/runtime.py": "56d4afe7ddb394b23d735c1f7b9e981c4a032963323ac50473f26b09ba9bd6ef",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46",
      "tests/unit/test_preview_scheduler.py": "42f7b5057fd0ef01e788a60e9201d7aad8e8e5a75e0d7b3174e11e3ed9b605dd",
      "tests/unit/test_audio_envelope.py": "5f51aa5ec09cbfc3283c0ef51cf8833363ce90609029f782de8edd4897ce8bde",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "tests/blender/test_result_previews.py": "a42261da4a269ef3e91b76f2260eca6d81d17831d51f29fb2c1cb62972e8b2e2",
      "tests/unit/test_result_transfers.py": "c7ce52c89e0423602fcfb8593b6b11530962169b4921a7df53cb33a8850dcf2d",
      "tests/blender/test_runtime_jobs.py": "56f200b664856a6ac44820ae48f605fc48b59a745733e70cf09d6e89278d29f4"
    }
  }
}
---

# Receipt-bound saved-result previews

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
