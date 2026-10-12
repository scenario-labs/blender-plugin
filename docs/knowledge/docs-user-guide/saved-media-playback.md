---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-media-playback",
  "title": "Play and waveform controls for saved video and audio",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4fbb69e1206ded60ada104df41a0d7c7617dad4b",
    "limits": "Reviewed the Video, Audio, panel summary and Files and folders claims about saved-result Play, Play in Blender and Waveform: their place in Jobs and Generations, private read-only copies named by the saved type, both players started without Scenario credentials in their environment, the animation player's two-player limit, offline operation, Cancel, Retry and close, receipt-keyed envelope reuse, retirement on a connection change or file load, and the format and size limits. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system player launcher and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Soundtrack playback in Blender's animation player is stated as unverified. The retained prototype controls' wording and the older panel screenshots were not re-reviewed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-reviewed on 2026-10-12 for the Video sentence that both players start without Scenario credentials: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment. Unit tests record the launch arguments and filtered environment per platform and refuse relative paths, and a stand-in POSIX xdg-open records the environment a real child process received; installed-ZIP native tests record the saved-result launcher, its pinned copy and a failed launch, and the retained prototype Play and Play in Blender operators. No real default player was started on any platform, and the Windows interpreter helper was not run on Windows. Since the earlier review main changed saved_job_actions.py, job_recovery.py and panels.py for first-frame, World, lane routing, history and model import controls, not the playback descriptors. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path. Re-checked on 2026-10-12 after the rebase onto main at c0ca235a, not a full re-review: main's saved Gaussian splat import changed job_session.py, job_recovery.py, runtime.py, saved_job_actions.py and their tests for splat import controls, options and session import notices; the rebase keeps the playback row after the job actions and before those notice and awaiting-review status rows, and leaves the playback descriptors, the player copies, their launchers and the waveform controller unchanged, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Also re-checked after the rebase onto main at ff8d29d8 (Environment lane, compact composer job strip), not a full re-review: panels.py gained draw_result(..., collapsible=False) for the composer's job card and studio.py a track_popup helper; the job strip dispatches only receipt, cancel, recover and apply descriptors, so the playback row is unchanged in Jobs, Generations and Studio and the job card draws the same panel rows. These fingerprints are the rebased files'.",
    "sources": {
      "scenario/blender/result_media.py": "71974d5fb92b52b825ce281cfbae747baf4c38169aa995c478fb21aa485749da",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "scenario/core/ui/saved_job_actions.py": "ff960aa1162afa47d079fa851016da620435dd0ff0bc50710de77b33d4aac4a2",
      "scenario/blender/job_recovery.py": "2f67afcea03d8c3db5ca51f1d9db2e11f559e4e94a788a1988fa6e90552fd077",
      "scenario/blender/panels.py": "ba62d496363b0dcb9e4c420eaf788da8d321f01def9a3b3bf4ab48edb30274ec",
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9",
      "tests/unit/test_playback.py": "09c7c327ec0adfd7ef0dc711797eaa6430234cf05784fbd2a4f897231af894ba"
    }
  }
}
---

# Play and waveform controls for saved video and audio

Evidence for [the canonical document](../../USER_GUIDE.md).
