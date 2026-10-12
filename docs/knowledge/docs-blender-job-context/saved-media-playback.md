---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-media-playback",
  "title": "Playback descriptors and player copy ownership",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4fbb69e1206ded60ada104df41a0d7c7617dad4b",
    "limits": "Reviewed the playback descriptors' saved-state and media-type conditions, their operators' context, revision and receipt checks, JobSession.prepare_playback and cancel_playback on the preview lane, and the controller's ownership: latest-request opening, reuse, the copy and player budgets, envelope-only waveform requests, scheduler cancellation, late-result rejection and cleanup on retirement, file load and unregister, including a persistent update timer that survives a file load and a retirement that first reaps exited animation players and system player launchers. Both player environments omit SCENARIO_, PYTHON and proxy variables. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system player launcher and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-reviewed on 2026-10-12 for the controller's system player launch: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment. The controller keeps each launcher with its copy, pins that copy until the launcher exits, reaps exited launchers before computing evictions, reports a launcher that exits with an error and clears launchers on unregister. Unit tests record the launch arguments and filtered environment per platform and refuse relative paths, and a stand-in POSIX xdg-open records the environment a real child process received; installed-ZIP native tests record the saved-result launcher, its pinned copy and a failed launch, and the retained prototype Play and Play in Blender operators. No real default player was started on any platform, and the Windows interpreter helper was not run on Windows. Since the earlier review main changed job_session.py, saved_job_actions.py, job_recovery.py and runtime.py for Film, first-frame, organization and model import controls; Main at 4fbb69e1 (saved OBJ, FBX, glTF and PLY mesh imports) changed job_recovery.py, job_session.py, runtime.py and saved_job_actions.py only for model import controls, not the playback descriptors, their row, the player copies or the waveform controller. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path. Re-checked on 2026-10-12 after the rebase onto main at c0ca235a, not a full re-review: main's saved Gaussian splat import changed job_session.py, job_recovery.py, runtime.py, saved_job_actions.py and their tests for splat import controls, options and session import notices; the rebase keeps the playback row after the job actions and before those notice and awaiting-review status rows, and leaves the playback descriptors, the player copies, their launchers and the waveform controller unchanged, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Also re-checked after the rebase onto main at 4f169337 (Film video export), which changed job_session.py, runtime.py and studio.py only for Film export controls and their labels, not the playback paths; these fingerprints are the rebased files'.",
    "sources": {
      "scenario/blender/job_session.py": "d061f201f2c31ff6db85cafe3082803cb7d60786b87cbaf9a1c4330408e9caa9",
      "scenario/blender/result_media.py": "71974d5fb92b52b825ce281cfbae747baf4c38169aa995c478fb21aa485749da",
      "scenario/core/ui/saved_job_actions.py": "ff960aa1162afa47d079fa851016da620435dd0ff0bc50710de77b33d4aac4a2",
      "scenario/blender/job_recovery.py": "2f67afcea03d8c3db5ca51f1d9db2e11f559e4e94a788a1988fa6e90552fd077",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "scenario/blender/runtime.py": "5f6c055f11afd021dbb331f2858be4044d24ccff0cf088765dfd0d0cefd1cecd",
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9"
    }
  }
}
---

# Playback descriptors and player copy ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
