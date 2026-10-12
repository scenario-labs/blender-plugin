---
{
  "type": "Evidence",
  "id": "docs-known-limitations.desktop-launches",
  "title": "Credential-free folder, file and link button limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "desktop-launches",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "ee7586fbe55fa8acc616a706958b1ae60026aee0",
    "limits": "Reviewed the bullet on folder, file and link buttons. scenario.open_path and scenario.open_url (scenario/blender/desktop.py, registered with the other Blender modules) call playback.system_open and the new playback.system_open_url, which share one launcher: /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment(), which drops SCENARIO_, PYTHON and proxy names, and with discarded output. system_open accepts absolute paths only; system_open_url accepts only https links with a host and without whitespace or control characters. The Output folder operator (operators.py) calls the same helper, and the Film capture panel's Open capture and Open capture files, the Film export and case-study Open folder, the preferences' Create a key in the portal link and the update controls' Update guide and Release ZIPs links (prefs.py, updates.py) now draw these operators instead of wm.path_open and wm.url_open. In the bundled scripts of the Blender 5.1.2 macOS application, read as files, wm.path_open calls os.startfile, open or xdg-open and wm.url_open calls Python's webbrowser (osascript on macOS, a browser command such as xdg-open on Linux, os.startfile on Windows), all with Blender's own environment. Unit tests record the commands and filtered environment per platform for files, folders and links, refuse other links before launching, and a stand-in POSIX xdg-open records the environment and argument a real child received for a file, a folder and a link; a unit-test AST scan of scenario/ finds no wm.path_open, wm.url_open, webbrowser, startfile or opener command outside playback.py, and found every direct use on main before this change. Installed-ZIP native tests draw each button into a recording layout, run its operator with recorded launchers, and run the real launchers with only the process faked to check the command and environment inside Blender. A missing or empty path and a refused link are reported by the operator before anything starts, as is a launcher that cannot start (OSError); a launcher that exits with a nonzero code is reported through runtime.set_message by a persistent timer polling every 0.25 s, which stops watching a launcher after 120 polls, about 30 seconds, without a report. No physical desktop check of these buttons was made; the private macOS check of open is carried from the saved-media-playback topic and covers the shared launcher, not the buttons. Real file managers and browsers on Windows and Linux, Linux without xdg-open and sandboxed Blender packages are stated as unverified.",
    "sources": {
      "scenario/blender/desktop.py": "1f34d2f730f4dc07c5734471aeedb84acf18f6b5f0fc83ca4d1de2dc4e67c496",
      "scenario/core/jobs/playback.py": "8592cb11e7a9883f085b9089ff3c252228f5122ef928f238a86205d333959ff3",
      "scenario/blender/operators.py": "43d5d38c8c82ad39a4399709f110bd45aeab8409ee0006c381ed63f410daf1a0",
      "scenario/blender/film_capture_controls.py": "ad684ec63686ac4bbade19f15ca6b2284c87d1134aecee3d2923a6900367f424",
      "scenario/blender/film_export_controls.py": "57a5c4970a47b7961a0494c5cfeb1ebcdef372f9bc9f7a9b50e7757e336d4d1e",
      "scenario/blender/film_case_study_controls.py": "d25d13da794567d07435e8ee4c942766e52661847039c04a66e3e795cba9592b",
      "scenario/blender/updates.py": "6678248428a6785dd0a2c0ba042338ee493c3a5da26f6471fc9fc3ad904d52b7",
      "scenario/prefs.py": "8501a51e598083a7414aa1c55c599001747e60caf57a0ce859402422880cf762",
      "scenario/blender/registry.py": "0802ea516ba4859b90e8ee9826f85d63a64358a75e8cd93e03d25fed244b83bf",
      "tests/unit/test_playback.py": "9f5fbab458e492c0fb7dc9948a3fbad6629ca32b0b2ee020fa6172f133073b1b",
      "tests/unit/test_system_openers.py": "76524bf50957b6389dc2bab78a8057d30d76c28f62b69da6d06ebe8f0fc4372c",
      "tests/blender/test_desktop_open.py": "9605dbcdf6bae02090de3dc3555b3f7cd30ec48e6f044f060d93a4149b11dcdb",
      "tests/blender/run_all.py": "5c130b9a348cef4bf95b09e4578a760feb22b014382663bff94caa4ebac8fa53"
    }
  }
}
---

# Credential-free folder, file and link button limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
