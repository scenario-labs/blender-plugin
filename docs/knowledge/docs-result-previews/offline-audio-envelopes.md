---
{
  "type": "Evidence",
  "id": "docs-result-previews.offline-audio-envelopes",
  "title": "Offline audio envelopes for saved results",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the offline decoder command line, scrubbed environment, disposable profile, timeout and cancellation mapping (a timeout only for a child still running at its deadline; a failed exit keeps its reported reason), the standalone worker's request checks, no-seek decode, sample and duration caps and fixed failure codes, the parent's header and block checks and EnvelopeBuilder folding, the scheduler's per-request lane dispatch, full-lane retry, missing-executable failure and close/release cleanup, and the session/runtime decoder specification. The GIL pause figures are local measurements of in-process decoding on a worker thread, not a test assertion. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Synthetic WAV, MP3, Ogg, FLAC, Matroska AAC and MP4 AAC only; no provider audio, sandboxed Blender package, antivirus or desktop acceptance. No UI or MCP view draws envelopes yet. No Scenario service call and no store schema change.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/preview_scheduler.py": "21d0b8d0265c2e70dc9d9c27372a8205bb6a10cfaeb5e896759705a37c0d482e",
      "scenario/core/jobs/results.py": "625d306accf972a65c20a01268be12c764d68eef48f2ae66d41b9fd1b8af17a1",
      "scenario/core/jobs/coordinator.py": "754bf1157082a887c30767c92e0f3a3604e2cfd4f1c5c6e15a118aee0e6b64ea",
      "scenario/core/jobs/workers.py": "3389e06b6ec12eba09291ae7d66194c47ec2a86170bbd5079413c56cbf9651b3",
      "scenario/core/jobs/local_render.py": "259ec65d914e12b8a8dce009ea68a07f4ab3ca1007a232a63a2c43fb64e5daaf",
      "scenario/blender/job_session.py": "9c6746c15fc4531eb132e28056abfaace4fdd94507300f37c59d18ebc0fa80d7",
      "scenario/blender/runtime.py": "286974e2a90e4776de71d081651a88424c543573add3ed125b072ad47c524883",
      "tests/unit/test_audio_decode.py": "3191b66bb5ed1cb995165ebe5f9736d06a84fb9effca42cd75a23dca41c31196",
      "tests/unit/test_audio_waveform.py": "8a165f722f77ca93f8ca5478ce913cea1b672677b6440f5f27e70d1d96201081",
      "tests/unit/test_preview_scheduler.py": "319ef441b2349165bdd4256144ec7448a35329d52a626c40cc2aea4670e15952",
      "tests/unit/test_result_previews.py": "1aaedd23563d63b78017e6bf72e33a825634a604abe105e8ab996fa4845b5929",
      "tests/unit/test_job_workers.py": "433229194bd6dc327f3f076f0f3c73ac919fb6df108a97bd6b99f9ff3346bca5",
      "tests/blender/test_waveform_worker.py": "b1fbfb74b8c75ef5366283ce32c97b23350bb1e81766891a2a7fab046b537aa5",
      "tests/blender/test_result_previews.py": "fd31993233db037d73220f4c5e67355da6af5688c864fbe2f62848f228af4c80"
    }
  }
}
---

# Offline audio envelopes for saved results

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
