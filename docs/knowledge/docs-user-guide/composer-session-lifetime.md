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
    "limits": "Reviewed the two composer sentences on a failure while handling the pointer or keyboard and on file loads against the composer modal, its load handler and ComposerState initialization. An error raised while the modal handles any event (click, key, pointer move or drag; the wrapper covers the whole modal method) leaves the prompt, ends the session and reaches Blender, which reports it; the next pointer move over the composer starts a new session. The persistent load handler re-initializes the composer state (collapsed, unfocused, empty field) and restores the offset and width saved in the preferences. Installed native tests in background Blender 5.1.2 on macOS arm64 cover a raised error during typing and three consecutive home-file loads; the UI style topic of the same scope records the runs, Blender source reading and limits. Not established, and tracked in the issue #66 comment 6120385854: Blender's window manager running these paths in an interface session (no event-simulated or physical check ran), how Blender's status bar shows the report, Open, Revert or File > New from the interface, physical input, and other Blender versions or operating systems. Rechecked after the cancel callback was made to leave a focused prompt as the error path does: the two sentences are unchanged, and a closed window, which the guide does not describe, now also leaves the prompt; the full installed suite (1,415 tests) passes on macOS arm64 Blender 5.1.2. Rechecked after rebasing onto main 3acb9625dc28bc74a6b764163ce6a6ca27144528 and its input-method text field: the two sentences are unchanged. F2 and a composition's second press are keyboard handling too: an error raised while they open the text field, other than the RuntimeError or AttributeError that call reports as a warning, also leaves the prompt and ends the session, and a new installed test checks that the next pointer move and click are accepted. The full installed suite (1,448 tests) passes on macOS arm64 Blender 5.1.2. Rechecked after _finish was made to restore the resize cursor that the pointer resting on the resize corner sets, when an error or the cancel callback ends the session there: the two sentences are unchanged and do not describe the cursor. The full installed suite (1,449 tests) passes on macOS arm64 Blender 5.1.2. Scoped 2026-10-12 check of the compact job strip rebased onto main, not a full re-review: the error wrapper and cancel callback still cover the whole modal handler, strip clicks included, and _invoke reports an error from a strip chip's operator as a warning without ending the session (UI_STYLE now says so); _finish still forgets the pending click and untyped press; the persistent _load_pre re-initializes the state, which now also forgets strip dismissals, drawn signatures and held actions; test_composer.py's error tests raise from the modal's geometry hook, which replaced its layout hook. The packaged ZIP passes 1,579 installed tests on macOS arm64 Blender 5.1.2. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-12 check of the job strip review fixes, not a full re-review: state.py only bounds the strip's dismissals and changes shown_actions; _load_pre still replaces the whole state, its strip caches included, and the session-end paths are unchanged. The packaged ZIP passes 1,630 installed tests on macOS arm64 Blender 5.1.2. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/composer/modal.py": "f6f0ad1b73e6baf2d682b1cf86c604727d635d7e98cded5f885223626a0944e9",
      "scenario/blender/composer/__init__.py": "561f7a9803b1f754202343e3c79cfb67b5851135a421042e34b57a9b3b54839e",
      "scenario/blender/composer/state.py": "22d2ba2af3d28915276b2e94897b97175bbe8445ae3fcc7d89422d39eff965ad",
      "tests/blender/test_composer.py": "4bf74b0e9ef0b9062e024fbd46932e58a84902a7bff0894ad4b93ae6a21ebe44",
      "tests/blender/helpers.py": "eb9b1148a436a61479cea0e8f69a02bd18eda96b8c265066ccd3d1ab5ec97ff7"
    }
  }
}
---

# Composer after a failed event and after a file load

Evidence for the [user guide's floating composer section](../../USER_GUIDE.md#the-floating-composer).
