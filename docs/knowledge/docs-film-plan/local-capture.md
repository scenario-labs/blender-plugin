---
{
  "type": "Evidence",
  "id": "docs-film-plan.local-capture",
  "title": "Owned local scene snapshots and background capture",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "local-capture",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "95d4eea95e4652f171ce0828db5af798008fa920",
    "limits": "Main-thread selected-scene export and bpy-free owned-process capture, adapted from the selected first-party Studio source. Exact blend snapshot hash, frame inventory and probed MP4 timing; external scene resources remain linked rather than frozen. Tests cover parent-state preservation, absent tools, invalid/tampered input, encoder failure retention and actual child cancellation/timeout cleanup. Local macOS arm64 Workbench PNG and MP4 probes on Blender 5.0.1, 5.1.2 and 5.2.1 use installed ffmpeg/ffprobe 8.0.1; this is not human motion/audio or Windows/Linux graphics acceptance. No registered capture UI/MCP command, new pool/store, upload or Scenario operation. Caller approval, shared-session cancellation/delivery, artifact cleanup and explicit upload handoff remain integration work. Native/update checks do not establish public release or hosted-update acceptance. Installed native tests verify inherited output flags are reset on the snapshot only and source settings remain unchanged. The regression intercepts the final GPU render operator; it establishes settings and routing, not rendered visual quality. Completed-media hashing scales with capture dimensions and frame count while retaining the prior 1 GiB floor; snapshot and staged-frame limits remain separate. Unit regressions use a sparse file larger than 1 GiB with simulated render/encode/probe processes to verify acceptance for a larger capture and retained rejection for a smaller one; they do not establish real large-video encoding.",
    "sources": {
      "scenario/blender/local_capture.py": "8fca341f2558601ab296604f6014e47b1212bbbc876a6cfefd93d4dce5fda8a9",
      "scenario/blender/render_worker.py": "9347be4926c1068022f26083bc8a7007f720d9d57e4e4140066db11cff6ec87c",
      "scenario/core/jobs/local_render.py": "431c26d4988c1f2c4ff5ac243a26e6e76dc53f0436b8a5775edede7917eedf8e",
      "tests/blender/test_local_capture.py": "798afc8105e4da8e57d56a0fde7cc943675f9337d89200748b8d05495001e02c",
      "tests/unit/test_local_render.py": "e62b9d7a05ca0064f2df9fe072c0c8ce4f19c5cf63a5fc07a8956341cbd9f405"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
