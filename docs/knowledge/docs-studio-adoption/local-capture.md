---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.local-capture",
  "title": "Owned local scene snapshots and background capture",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "local-capture",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Main-thread selected-scene export and bpy-free owned-process capture, adapted from the selected first-party Studio source. Exact blend snapshot hash, frame inventory and probed MP4 timing; external scene resources remain linked rather than frozen. Tests cover parent-state preservation, absent tools, invalid/tampered input, encoder failure retention and actual child cancellation/timeout cleanup. Local macOS arm64 Workbench PNG and MP4 probes on Blender 5.0.1, 5.1.2 and 5.2.1 use installed ffmpeg/ffprobe 8.0.1; this is not human motion/audio or Windows/Linux graphics acceptance. No registered capture UI/MCP command, new pool/store, upload or Scenario operation. Caller approval, shared-session cancellation/delivery, artifact cleanup and explicit upload handoff remain integration work. Native/update checks do not establish public release or hosted-update acceptance.",
    "sources": {
      "scenario/blender/local_capture.py": "8fca341f2558601ab296604f6014e47b1212bbbc876a6cfefd93d4dce5fda8a9",
      "scenario/blender/render_worker.py": "224422fa310a8b3c1515218828d67eb33182de79849647d4dde3c6b099f3a281",
      "scenario/core/jobs/local_render.py": "e1b66441cffa68baa1c3ab5a5045c11a0ec183a15e17a46bdced50306c9fb930",
      "tests/blender/test_local_capture.py": "757312e55cead2fbeaae746247d5b81acda965541295c7618bf3385aee11d9eb",
      "tests/unit/test_local_render.py": "099b2308fc32995087dbce143740d73fcf3c51a051d4a8435a928b54325175f0"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
