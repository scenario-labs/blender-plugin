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
    "limits": "Reviewed where Play copies are written (cache/media-playback), their read-only private storage, the reuse budget, removal on a connection change, file load or extension disable unless a running animation player or system player launcher uses them, and the day-old sweep. Re-reviewed on 2026-10-12 for the player environments: both players start without SCENARIO_, PYTHON or proxy variables. playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment. The saved-result controls (result_media) and the retained prototype Play and Play in Blender operators (apply_video, through operators.py) use these launchers, and apply_audio's unused system opener was removed. A player that is already running is reached by the operating system, not by a new process with this environment. Unit tests record the launch arguments and filtered environment per platform and refuse relative paths, and a stand-in POSIX xdg-open records the environment a real child process received; installed-ZIP native tests record the saved-result launcher, its pinned copy and a failed launch, and the retained prototype Play and Play in Blender operators. No real default player was started on any platform, and the Windows interpreter helper was not run on Windows. What the operating system's default player records is outside this review. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it and predate the new launcher. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path. Also on 2026-10-12, the player environment wording now says the launches strip SCENARIO_, PYTHON and proxy variables from the environment Blender passes, after a private physical check on macOS 27 arm64 Blender 5.1.2 with Environment credentials and a ZIP built from the branch before its later review fixes: Play opened the system player on the private read-only copy, whose SHA-256 matched the saved result, and Play in Blender started a player whose environment had no SCENARIO_, PYTHON or proxy names. The system player's own environment cannot be read on macOS; ad-hoc probe applications launched through the macOS open command showed that it passes its caller's whole environment, that the filtered launch delivered no SCENARIO_ or PYTHON names, and that macOS adds login-session proxy variables to every launched application whatever the caller passes, which the documents now state. Windows and Linux launchers were not exercised on real systems. Source fingerprints are unchanged by this wording note. Re-checked on 2026-10-12 after the folder and link buttons moved to the same launcher: system_open keeps its absolute-path check, commands, environment and discarded output, now through a launcher shared with the new system_open_url, and its refusal messages no longer name players; the player claims above are unchanged, and the buttons are covered by the desktop-launches topic. This topic's fingerprints for the sources that change touched were updated with this check.",
    "sources": {
      "scenario/core/jobs/playback.py": "8592cb11e7a9883f085b9089ff3c252228f5122ef928f238a86205d333959ff3",
      "scenario/blender/result_media.py": "71974d5fb92b52b825ce281cfbae747baf4c38169aa995c478fb21aa485749da",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "tests/unit/test_playback.py": "9f5fbab458e492c0fb7dc9948a3fbad6629ca32b0b2ee020fa6172f133073b1b",
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9",
      "scenario/blender/apply_video.py": "48e4654a7601c2ec5d52302a0ba59968eded05e9dca838207402ca74c772ad61",
      "scenario/blender/operators.py": "43d5d38c8c82ad39a4399709f110bd45aeab8409ee0006c381ed63f410daf1a0"
    }
  }
}
---

# Local player copies of saved media

Evidence for [the canonical policy](../../PRIVACY.md).
