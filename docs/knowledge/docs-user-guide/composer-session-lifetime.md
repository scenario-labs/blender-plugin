---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-session-lifetime",
  "title": "Composer after a failed event and after a file load",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-session-lifetime",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed the two composer sentences on a failure while handling the pointer or keyboard and on file loads against the composer modal, its load handler and ComposerState initialization. An error raised while the modal handles any event (click, key, pointer move or drag; the wrapper covers the whole modal method) leaves the prompt, ends the session and reaches Blender, which reports it; the next pointer move over the composer starts a new session. The persistent load handler re-initializes the composer state (collapsed, unfocused, empty field) and restores the offset and width saved in the preferences. Installed native tests in background Blender 5.1.2 on macOS arm64 cover a raised error during typing and three consecutive home-file loads; the UI style topic of the same scope records the runs, Blender source reading and limits. Not established, and tracked in the issue #66 comment 6120385854: Blender's window manager running these paths in an interface session (no event-simulated or physical check ran), how Blender's status bar shows the report, Open, Revert or File > New from the interface, physical input, and other Blender versions or operating systems. Rechecked after the cancel callback was made to leave a focused prompt as the error path does: the two sentences are unchanged, and a closed window, which the guide does not describe, now also leaves the prompt; the full installed suite (1,415 tests) passes on macOS arm64 Blender 5.1.2.",
    "sources": {
      "scenario/blender/composer/modal.py": "89fed68b6d8032f003b9b0a9b5d9ba39d4c781fbb1251e44bd0ad7a4ab008e24",
      "scenario/blender/composer/__init__.py": "9135da55599d3d9a0a63be6e9528571c7cf62b4164fbb55811e3682b9a6b27d6",
      "scenario/blender/composer/state.py": "943d2b3410966c62a00ef7b4a3251a66727f761e5b556e91565ec29d22c50ed4",
      "tests/blender/test_composer.py": "344bf689f834934aabaecbc89c004a94cd18d5b99c6bcfcd7cc2dddc81c2478a",
      "tests/blender/helpers.py": "eb9b1148a436a61479cea0e8f69a02bd18eda96b8c265066ccd3d1ab5ec97ff7"
    }
  }
}
---

# Composer after a failed event and after a file load

Evidence for the [user guide's floating composer section](../../USER_GUIDE.md#the-floating-composer).
