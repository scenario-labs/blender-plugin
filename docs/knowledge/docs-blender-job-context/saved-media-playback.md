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
    "limits": "Reviewed the playback descriptors' saved-state and media-type conditions, their operators' context, revision and receipt checks, JobSession.prepare_playback and cancel_playback on the preview lane, and the controller's ownership: latest-request opening, reuse, the copy and player budgets, envelope-only waveform requests, scheduler cancellation, late-result rejection and cleanup on retirement, file load and unregister, including a persistent update timer that survives a file load and a retirement that first reaps exited animation players and system player launchers. Both player environments omit SCENARIO_, PYTHON and proxy variables. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system player launcher and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-reviewed on 2026-10-12 for the controller's system player launch: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment. The controller keeps each launcher with its copy, pins that copy until the launcher exits, reaps exited launchers before computing evictions, reports a launcher that exits with an error and clears launchers on unregister. Unit tests record the launch arguments and filtered environment per platform and refuse relative paths, and a stand-in POSIX xdg-open records the environment a real child process received; installed-ZIP native tests record the saved-result launcher, its pinned copy and a failed launch, and the retained prototype Play and Play in Blender operators. No real default player was started on any platform, and the Windows interpreter helper was not run on Windows. Since the earlier review main changed job_session.py, saved_job_actions.py, job_recovery.py and runtime.py for Film, first-frame, organization and model import controls; Main at 4fbb69e1 (saved OBJ, FBX, glTF and PLY mesh imports) changed job_recovery.py, job_session.py, runtime.py and saved_job_actions.py only for model import controls, not the playback descriptors, their row, the player copies or the waveform controller.",
    "sources": {
      "scenario/blender/job_session.py": "5b35e3627eaa7dbf33ed982273177b7e1669a5d9869cf84741534e3c3b46f534",
      "scenario/blender/result_media.py": "a7bae9b893ccaffc117f9c4b5dfbd5d9f337d867239e8caf8a4d290eb8fbc429",
      "scenario/core/ui/saved_job_actions.py": "a93620d09c46953a1679f642e5dcf26f1c8fa59391b0b999e089f59648a9d33e",
      "scenario/blender/job_recovery.py": "0902adfae88080406320a9f8770f5221a3f7441ac19e5d7c468abaf4dbaa8f34",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "scenario/blender/runtime.py": "184975579304728ea00b3d84bc7d4bee5b308380bfa923a97aeb2f8cdc23d518",
      "tests/blender/test_result_media.py": "1691143a5c0673fd811651255980faa939a425fbd0837b8eaffc4c86229b6bdd"
    }
  }
}
---

# Playback descriptors and player copy ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
