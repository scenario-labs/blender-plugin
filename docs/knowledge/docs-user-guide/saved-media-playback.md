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
    "limits": "Reviewed the Video, Audio, panel summary and Files and folders claims about saved-result Play, Play in Blender and Waveform: their place in Jobs and Generations, private read-only copies named by the saved type, both players started without Scenario credentials in their environment, the animation player's two-player limit, offline operation, Cancel, Retry and close, receipt-keyed envelope reuse, retirement on a connection change or file load, and the format and size limits. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system player launcher and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Soundtrack playback in Blender's animation player is stated as unverified. The retained prototype controls' wording and the older panel screenshots were not re-reviewed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-reviewed on 2026-10-12 for the Video sentence that both players start without Scenario credentials: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment. Unit tests record the launch arguments and filtered environment per platform and refuse relative paths, and a stand-in POSIX xdg-open records the environment a real child process received; installed-ZIP native tests record the saved-result launcher, its pinned copy and a failed launch, and the retained prototype Play and Play in Blender operators. No real default player was started on any platform, and the Windows interpreter helper was not run on Windows. Since the earlier review main changed saved_job_actions.py, job_recovery.py and panels.py for first-frame, World, lane routing, history and model import controls, not the playback descriptors.",
    "sources": {
      "scenario/blender/result_media.py": "a7bae9b893ccaffc117f9c4b5dfbd5d9f337d867239e8caf8a4d290eb8fbc429",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "scenario/core/ui/saved_job_actions.py": "a93620d09c46953a1679f642e5dcf26f1c8fa59391b0b999e089f59648a9d33e",
      "scenario/blender/job_recovery.py": "0902adfae88080406320a9f8770f5221a3f7441ac19e5d7c468abaf4dbaa8f34",
      "scenario/blender/panels.py": "a2cb353c67f0f4dc834e76432795a7d3fd8cd1df5ceca9faf0f7bfe9b4ce6fd9",
      "tests/blender/test_result_media.py": "1691143a5c0673fd811651255980faa939a425fbd0837b8eaffc4c86229b6bdd",
      "tests/unit/test_playback.py": "09c7c327ec0adfd7ef0dc711797eaa6430234cf05784fbd2a4f897231af894ba"
    }
  }
}
---

# Play and waveform controls for saved video and audio

Evidence for [the canonical document](../../USER_GUIDE.md).
