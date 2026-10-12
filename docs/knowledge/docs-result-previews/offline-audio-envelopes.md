---
{
  "type": "Evidence",
  "id": "docs-result-previews.offline-audio-envelopes",
  "title": "Offline audio envelopes for saved results",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "759f764dff9c9d9b1f50efecdd46835471f19189",
    "limits": "Inspected the offline decoder command line, scrubbed environment, disposable profile, timeout and cancellation mapping (a timeout only for a child still running at its deadline; a failed exit keeps its reported reason), the standalone worker's request checks, no-seek decode, sample and duration caps and fixed failure codes, the parent's header and block checks and EnvelopeBuilder folding, the scheduler's per-request lane dispatch, full-lane retry, missing-executable failure and close/release cleanup, an explicit retry that leaves a running offline decode to settle and withdraws an envelope still waiting for room on the lane, and the session/runtime decoder specification. The GIL pause figures are local measurements of in-process decoding on a worker thread, not a test assertion. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed locally on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Hosted CI run 38020273661 at b6f6b348, whose code and tests this head keeps, built and installed its own ZIP in each Blender baseline job on Linux x64 (ubuntu-24.04) and Windows x64 (windows-2025) runners for Blender 5.0.1, 5.1.2 and 5.2.1; each of the six jobs passed 765 native tests (skipped=2, none of them audio), including all six test_waveform_worker tests, among them the seven-format decode parity test, and all seven test_result_previews tests. Synthetic WAV, MP3, Ogg, FLAC, Matroska AAC and MP4 AAC only; no provider audio, macOS x64, sandboxed Blender package, child start-up timing or antivirus behavior on real Windows and Linux desktops, or desktop acceptance. The lane occupancy figures are macOS arm64 measurements. No UI or MCP view draws envelopes yet. No Scenario service call and no store schema change. Re-checked after the native main-thread lock test failed on hosted CI run 38239474711 (Blender 5.2.1 on Linux and Windows, pauses of 0.110 and 0.100 s against a fixed 0.1 s bound): the test now decodes the same five-minute stereo MP3 in process as a control, requires that control to pause the main thread for more than half its length, and bounds the offline decode's longest main-thread pause at half the control's pause, with automatic garbage collection paused during both measurements. The ten-minute 0.4 to 0.55 s figures remain local measurements, not a test assertion; the five-minute control paused the main thread for 0.26 to 0.28 s locally on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. A temporary in-process mutation of audio_decode.decode failed the bound on Blender 5.1.2 (0.260 s pause against a 0.267 s control). Other drifted sources in this topic were not re-reviewed.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/preview_scheduler.py": "df19ea81e2b0afb1628ce345f0c45fa918f0d64195a3a37ed3360f95fb7e8e78",
      "scenario/core/jobs/results.py": "05e5c0997917e8fc242f799e73960666873328f23e1ab5518892a4ac49f82c0a",
      "scenario/core/jobs/coordinator.py": "57ce1e03e38f9346452d9e71e2942b46bc44fdcccd17c695a4272affc74bce2d",
      "scenario/core/jobs/workers.py": "df2830bcfd58445dcf67845e605f49a0305a103275a0aa8bf3d52450ae9a3658",
      "scenario/core/jobs/local_render.py": "259ec65d914e12b8a8dce009ea68a07f4ab3ca1007a232a63a2c43fb64e5daaf",
      "scenario/blender/job_session.py": "eca075ce7911e8aae4c5ee2746aaa8d4b1dcb6b40538723de437be4104948124",
      "scenario/blender/runtime.py": "628771d9cdda2fad47c506a4e5571727103ec3b6549c289eb3a8571ba96fffe0",
      "tests/unit/test_audio_decode.py": "3191b66bb5ed1cb995165ebe5f9736d06a84fb9effca42cd75a23dca41c31196",
      "tests/unit/test_audio_waveform.py": "8a165f722f77ca93f8ca5478ce913cea1b672677b6440f5f27e70d1d96201081",
      "tests/unit/test_preview_scheduler.py": "5949e57a0ceb148c514de2bc634eea8951b9de7ace8fe8f2e5377da4832128c0",
      "tests/unit/test_result_previews.py": "39bd9c984b9e8c93a078b677bbe398167ed72fa57803f7db7f73320cf2ff548d",
      "tests/unit/test_job_workers.py": "433229194bd6dc327f3f076f0f3c73ac919fb6df108a97bd6b99f9ff3346bca5",
      "tests/blender/test_waveform_worker.py": "5e03524a94fcedee799c9030c9b6a17ee872d9b8982349602c60bb369a62a230",
      "tests/blender/test_result_previews.py": "fd31993233db037d73220f4c5e67355da6af5688c864fbe2f62848f228af4c80",
      "tests/blender/run_all.py": "1ede97e95898fdc7d2cb8ddfaff1bc4fd7325cd64258ee9797d041c8b7675199",
      ".github/workflows/blender-baseline.yml": "831c887cf2b56795e934a60d40fa3c9cd93de7d7d8cf2977589548ed01413022"
    }
  }
}
---

# Offline audio envelopes for saved results

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
