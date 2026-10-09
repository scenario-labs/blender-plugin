---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the main-thread export snapshot (view-layer sync, blocked strip types, distinct-file media stamps, Blender's truncated default size), specification bounds, offline child arguments and environment, built-in FFmpeg settings including the explicit 8-bit depth, bounded progress, the live 64 MiB free-space floor, container inspection, ffprobe and Blender decode verification, the cancellable final hash, destination validation, the exclusive placeholder held open on POSIX, the exact-size publish space check, identity-checked publish with a last cancellation check, copy-only re-publish and session-owned thread ownership. Unit tests use synthetic MP4 boxes and simulated processes; the Blender fallback does not decode every frame or report pixel format. At this revision a local macOS arm64 run of the full installed suite passes on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. Destination names follow Python 3.13 ntpath.isreserved rules (checked against it locally); containment compares Windows extended and ordinary spellings, folds case and Unicode composition on every platform and refuses empty or relative private roots; the hidden partial file has a fixed-length name, so a 255-byte destination publishes. Reused snapshots are refused before hashing and staging or report OSErrors become path-free errors. A build lacking an H.264 or AAC encoder is not detected before rendering and was not exercised; it surfaces as the generic child failure. Linux inode reuse defeated the placeholder identity check in CI; the pinned reservation was verified red/green in a local Linux container. Windows placeholder identity relies on NTFS file IDs and is not exercised separately. The 8-bit test pins the setting only: Blender 5.0.1 and 5.1.2 already reset the depth when the file format is assigned.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/job_session.py": "070652fa2d92e43b01989823ef4bd20bc43bc6559a131a43297afc9b3ce8a498",
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/blender/run_all.py": "76114be12bc10852c9ba6c434552618d44cc840fc5adf6e9bafa49226682ebd6",
      "tests/blender/test_film_export_primitive.py": "ab91fa90c80dea9dc1e06edfb53e7741b647c72f8a0297562b195302983e2fdc",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945",
      "tests/unit/test_local_render.py": "4664d870acdbf83a539e3c0437288973e0d500d112eaaaa0490e1eebf9f411b5"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
