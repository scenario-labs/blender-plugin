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
    "limits": "Main-thread selected-scene export and bpy-free owned-process capture, adapted from the selected first-party Studio source. Exact blend snapshot hash, frame inventory and probed MP4 timing; external scene resources remain linked rather than frozen. Tests cover parent-state preservation, absent tools, invalid/tampered input, encoder failure retention and actual child cancellation/timeout cleanup. Local macOS arm64 Workbench PNG and MP4 probes on Blender 5.0.1, 5.1.2 and 5.2.1 use installed ffmpeg/ffprobe 8.0.1; this is not human motion/audio or Windows/Linux graphics acceptance. No registered capture UI/MCP command, new pool/store, upload or Scenario operation. Caller approval, shared-session cancellation/delivery, artifact cleanup and explicit upload handoff remain integration work. Native/update checks do not establish public release or hosted-update acceptance. Installed native tests verify inherited output flags are reset on the snapshot only and source settings remain unchanged. The regression intercepts the final GPU render operator; it establishes settings and routing, not rendered visual quality. Completed-media hashing scales with capture dimensions and frame count while retaining the prior 1 GiB floor; snapshot and staged-frame limits remain separate. Unit regressions use a sparse file larger than 1 GiB with simulated render/encode/probe processes to verify acceptance for a larger capture and retained rejection for a smaller one; they do not establish real large-video encoding. Windows capture paths use ordinary drive/UNC syntax at the Blender boundary while Python retains extended storage paths. Long snapshot destinations are rejected before export with staging cleanup; baseline native tests cover real ordinary-path snapshot export/child load and Windows-only deep-path rejection. The child inspection fixture emits a synthetic PNG header and does not exercise Windows GPU rendering or a real UNC share. Real-child unit regressions force successful exit before the first poll and verify exact-limit acceptance and one-byte overflow rejection for combined logs, separate stderr and probe stdout. Diagnostic checks run during polling and after exit; they do not prevent transient disk growth between checks. Child profile and temporary-path validation precedes exclusive capture admission; rejection removes scratch directories and preserves the unclaimed snapshot. Unit tests exercise both rejected child paths, subsequent successful admission and duplicate-start rejection. A Windows-only native regression exports a fitting snapshot and verifies that longer child paths fail without a start marker or frame directory; its execution requires Windows CI.",
    "sources": {
      "scenario/blender/local_capture.py": "1971034181539262983fd979526b9f71004225a1658010d22ffd749ad6110ed4",
      "scenario/blender/render_worker.py": "9347be4926c1068022f26083bc8a7007f720d9d57e4e4140066db11cff6ec87c",
      "scenario/core/jobs/local_render.py": "37c57537f75172892b868c56c9e0bcb641617c271ec1dae5a037e96ecabaeaf8",
      "tests/blender/test_local_capture.py": "4cc99c9440e949efc3da12b78f8b2b170c07eca5faf5aec3a47248d6b2f2b519",
      "tests/unit/test_local_render.py": "c9419e69af6a51184116618992e5e66f714d631ed20f49750ee40f47efb6e9eb",
      "tests/blender/run_all.py": "bd3dcb28911ceb9ed42522c8ada38e2d45c4769c571173ed5d9f942eb2130373"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
