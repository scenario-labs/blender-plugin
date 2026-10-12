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
    "base_revision": "3acb9625dc28bc74a6b764163ce6a6ca27144528",
    "limits": "Reviewed the two composer sentences on a failure while handling the pointer or keyboard and on file loads against the composer modal, its load handler and ComposerState initialization. An error raised while the modal handles any event (click, key, pointer move or drag; the wrapper covers the whole modal method) leaves the prompt, ends the session and reaches Blender, which reports it; the next pointer move over the composer starts a new session. The persistent load handler re-initializes the composer state (collapsed, unfocused, empty field) and restores the offset and width saved in the preferences. Installed native tests in background Blender 5.1.2 on macOS arm64 cover a raised error during typing and three consecutive home-file loads; the UI style topic of the same scope records the runs, Blender source reading and limits. Not established, and tracked in the issue #66 comment 6120385854: Blender's window manager running these paths in an interface session (no event-simulated or physical check ran), how Blender's status bar shows the report, Open, Revert or File > New from the interface, physical input, and other Blender versions or operating systems. Rechecked after the cancel callback was made to leave a focused prompt as the error path does: the two sentences are unchanged, and a closed window, which the guide does not describe, now also leaves the prompt; the full installed suite (1,415 tests) passes on macOS arm64 Blender 5.1.2. Rechecked after rebasing onto main 3acb9625dc28bc74a6b764163ce6a6ca27144528 and its input-method text field: the two sentences are unchanged. F2 and a composition's second press are keyboard handling too: an error raised while they open the text field, other than the RuntimeError or AttributeError that call reports as a warning, also leaves the prompt and ends the session, and a new installed test checks that the next pointer move and click are accepted. The full installed suite (1,448 tests) passes on macOS arm64 Blender 5.1.2.",
    "sources": {
      "scenario/blender/composer/modal.py": "24eb5da45b5ad27ca5692751a2bd8cb9ff92a19770a26ffa8efaf9ffcf164c52",
      "scenario/blender/composer/__init__.py": "ef390f9bf163c5a47216a4e660f8e29466e24810185c14b878eb4bbe34342fc8",
      "scenario/blender/composer/state.py": "cb95d81f7b301c2f527c7de361c9ef39f864f43f422d566b0abe1fcebc50d982",
      "tests/blender/test_composer.py": "352bcf7a5933afd31b271d2576054a41652e89d9fe92a00fd8c86cc15414681e",
      "tests/blender/helpers.py": "eb9b1148a436a61479cea0e8f69a02bd18eda96b8c265066ccd3d1ab5ec97ff7"
    }
  }
}
---

# Composer after a failed event and after a file load

Evidence for the [user guide's floating composer section](../../USER_GUIDE.md#the-floating-composer).
