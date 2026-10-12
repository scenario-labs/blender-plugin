---
{
  "type": "Evidence",
  "id": "docs-privacy.saved-media-playback",
  "title": "Local player copies of saved media",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4fbb69e1206ded60ada104df41a0d7c7617dad4b",
    "limits": "Reviewed where Play copies are written (cache/media-playback), their read-only private storage, the reuse budget, removal on a connection change, file load or extension disable unless a running animation player or system player launcher uses them, and the day-old sweep. Re-reviewed on 2026-10-12 for the player environments: both players start without SCENARIO_, PYTHON or proxy variables. playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment. The saved-result controls (result_media) and the retained prototype Play and Play in Blender operators (apply_video, through operators.py) use these launchers, and apply_audio's unused system opener was removed. A player that is already running is reached by the operating system, not by a new process with this environment. Unit tests record the launch arguments and filtered environment per platform and refuse relative paths, and a stand-in POSIX xdg-open records the environment a real child process received; installed-ZIP native tests record the saved-result launcher, its pinned copy and a failed launch, and the retained prototype Play and Play in Blender operators. No real default player was started on any platform, and the Windows interpreter helper was not run on Windows. What the operating system's default player records is outside this review. Opening the Output folder, a Film capture folder, the portal and update links still use Blender's wm.path_open and wm.url_open, outside this topic's claims. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it and predate the new launcher.",
    "sources": {
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "scenario/blender/result_media.py": "a7bae9b893ccaffc117f9c4b5dfbd5d9f337d867239e8caf8a4d290eb8fbc429",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "tests/unit/test_playback.py": "09c7c327ec0adfd7ef0dc711797eaa6430234cf05784fbd2a4f897231af894ba",
      "tests/blender/test_result_media.py": "1691143a5c0673fd811651255980faa939a425fbd0837b8eaffc4c86229b6bdd",
      "scenario/blender/apply_video.py": "48e4654a7601c2ec5d52302a0ba59968eded05e9dca838207402ca74c772ad61",
      "scenario/blender/operators.py": "492ff2344e7e5c2cac8d9413021f942dc98aee367f477920f9b4e6adaa58394d"
    }
  }
}
---

# Local player copies of saved media

Evidence for [the canonical policy](../../PRIVACY.md).
