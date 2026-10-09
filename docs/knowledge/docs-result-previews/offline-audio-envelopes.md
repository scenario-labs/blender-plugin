---
{
  "type": "Evidence",
  "id": "docs-result-previews.offline-audio-envelopes",
  "title": "Offline audio envelopes for saved results",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the offline decoder command line, scrubbed environment, disposable profile, timeout and cancellation mapping, the standalone worker's request checks, no-seek decode, sample and duration caps and fixed failure codes, the parent's header and block checks and EnvelopeBuilder folding, the scheduler's per-request lane dispatch, full-lane retry, missing-executable failure and close/release cleanup, and the session/runtime decoder specification. The GIL pause figures are local measurements of in-process decoding on a worker thread, not a test assertion. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Synthetic WAV, MP3, Ogg, FLAC, Matroska AAC and MP4 AAC only; no provider audio, sandboxed Blender package, antivirus or desktop acceptance. No UI or MCP view draws envelopes yet. No Scenario service call and no store schema change.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "332645a336308d1a52690fa55b888073fffff5213f95cc59460a2314ca973720",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/result_previews.py": "1bc82a1318619cb3771377caa6db67d107d6180a85575fbcc2d5470c087e5467",
      "scenario/core/jobs/preview_scheduler.py": "259ba661bb90b15d33723bfd7bafc0eb70b4443b5c8a56e70d45b9ffa99ac466",
      "scenario/core/jobs/results.py": "58491953638b6401ec26771c8eb98ee5ff79019cd1708888398800ca32d1c813",
      "scenario/core/jobs/coordinator.py": "6c84cbc7bdac5c0b130d8afc859faa95a06b1bfe8390449f8e8ceab61263391b",
      "scenario/core/jobs/workers.py": "fb361cbf1291e9dc426502ba4eaf6a538bebd15a80da9f02dacac8c8fa466dc9",
      "scenario/core/jobs/local_render.py": "37c57537f75172892b868c56c9e0bcb641617c271ec1dae5a037e96ecabaeaf8",
      "scenario/blender/job_session.py": "3dd23377c9c1883be489a8af292984c5af606a3c85a1bdb39981906b7c2767bd",
      "scenario/blender/runtime.py": "1c597c458a32872241b53724886fb7ba89efd9a6b5b2a3c7daeb2c94d1b5d401",
      "tests/unit/test_audio_decode.py": "2497b7c0ed39848d6051634b6b4809422f9b9c5eaaa56320ec47ddf92057d633",
      "tests/unit/test_audio_waveform.py": "8a165f722f77ca93f8ca5478ce913cea1b672677b6440f5f27e70d1d96201081",
      "tests/unit/test_preview_scheduler.py": "06c9ed59a866565734aa8abdb08b6e71ed925ad1253eaee9ef830a189618ff87",
      "tests/unit/test_result_previews.py": "d571f7848c51872570a9207a42a393e9b40e01b3e7ed8f0b9d7a2b545572addb",
      "tests/unit/test_job_workers.py": "433229194bd6dc327f3f076f0f3c73ac919fb6df108a97bd6b99f9ff3346bca5",
      "tests/blender/test_waveform_worker.py": "b1fbfb74b8c75ef5366283ce32c97b23350bb1e81766891a2a7fab046b537aa5",
      "tests/blender/test_result_previews.py": "5b389797a45805c3c80966e6ee1ab4a07e36b6ad90b5ae3b7daf0139c9fbfb69"
    }
  }
}
---

# Offline audio envelopes for saved results

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
