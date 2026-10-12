---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-session-lifetime",
  "title": "Composer after a failed click or key and after a file load",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-session-lifetime",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed the two composer sentences on a failed click or key and on file loads against the composer modal, its load handler and ComposerState initialization. An error raised while the modal handles a click or key leaves the prompt, ends the session and reaches Blender, which reports it; the next pointer move over the composer starts a new session. The persistent load handler re-initializes the composer state (collapsed, unfocused, empty field) and restores the offset and width saved in the preferences. Installed native tests in background Blender 5.1.2 on macOS arm64 cover a raised error during typing and three consecutive home-file loads; the UI style topic of the same scope records the runs, Blender source reading and limits. Not established: how Blender's status bar shows the report, Open, Revert or File > New from the interface, physical input, and other Blender versions or operating systems.",
    "sources": {
      "scenario/blender/composer/modal.py": "968819bc3ec818fd5e7afe8ebe801832c66b65556251366da456d2043171a27e",
      "scenario/blender/composer/__init__.py": "9135da55599d3d9a0a63be6e9528571c7cf62b4164fbb55811e3682b9a6b27d6",
      "scenario/blender/composer/state.py": "943d2b3410966c62a00ef7b4a3251a66727f761e5b556e91565ec29d22c50ed4",
      "tests/blender/test_composer.py": "6eadb29d4e7bf1e975e541ad2396768591132876bcea9f4ae268106e4a4ae777",
      "tests/blender/helpers.py": "eb9b1148a436a61479cea0e8f69a02bd18eda96b8c265066ccd3d1ab5ec97ff7"
    }
  }
}
---

# Composer after a failed click or key and after a file load

Evidence for the [user guide's floating composer section](../../USER_GUIDE.md#the-floating-composer).
