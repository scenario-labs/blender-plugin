---
{
  "type": "Evidence",
  "id": "docs-ui-style.composer-session-lifetime",
  "title": "Composer session lifetime after errors and file loads",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "composer-session-lifetime",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Source-reviewed the composer modal's invoke, _finish, cancel and modal entry points, its Generate helper, the load handler and registration, ComposerState initialization and the Generate operator's poll and error report. The running flag is set only by invoke and cleared by _finish (which the new error path and cancel callback call), the load handler, registration and runtime state initialization. Blender's v5.1.2 source was read for the lifetime claims: rna_operator_modal_cb leaves the modal result at its FINISHED default when the Python call fails, and the event loop then frees the operator and removes its handler without calling cancel; WM_event_remove_handlers calls an operator's cancel callback, which Python operators have only when their class defines cancel, and both the file-read window setup and wm_window_free call it for every window's modal handlers; a data file load runs the load_pre callbacks, then BPY_python_reset, whose BPY_app_handlers_reset(false) removes every handler without the persistent mark. Installed native tests on the packaged ZIP 0d64e5be1c5e87297ae2a9d9c1459c6f07acd32867c2f5957ec28e84ab193be8 in background Blender 5.1.2 on macOS arm64 call the operator's invoke, modal and cancel with a stand-in operator object: a Generate whose real operator poll is refused by the GUI spend guard (reported as one warning, the session continues and the next click focuses the prompt), a ValueError raised while a key is typed in the focused prompt (re-raised, the flag cleared, focus left, the prompt unchanged and the next invoke and click accepted), cancel during a pending card drag (flag cleared, placement restored, next invoke accepted), and three consecutive read_homefile loads with the card expanded, focused and marked running. With the previous composer code (unchanged between main 5f6fb8a9473e321090cb4749ef1ac66d252c84aa and this base revision) and these tests, the full installed suite ran 1,399 tests with 2 failures and 1 error, all three in the new error, file-load and cancel tests; the spend guard test passed there because Generate refusals were already caught. With this change the full suite passed with 1,399 tests on that earlier main and with 1,414 tests on this base revision (the ZIP above); one earlier run on this base revision had a single unrelated error in a blockout job refresh test under heavy machine load. The error path wraps the whole modal method, so a pointer move or drag that raises takes it as well as a click or key; only the key case is tested. The real window manager never ran these handlers: no GUI or physical session, no closed window, no Open, Revert or File > New from the interface, and no Blender 5.0, 5.2, Windows or Linux run. A background probe on Blender 5.1.2 macOS arm64 (factory startup, a minimal Python modal operator) showed why the installed tests call the handlers directly: an INVOKE_DEFAULT call with a window, area and region override was refused as an invalid operator call and never reached invoke, so background Blender cannot start the modal through its window manager. No event-simulated GUI check (--enable-event-simulate) ran for this change because it was prepared without opening a Blender window; the issue #66 comment 6120385854 records that check (a file load during a running session, an error raised while a simulated key is handled) and the two physical rechecks, each with its expected result. The physical finding is summarized from a private desktop report on Blender 5.1.2 macOS; the fix has not been physically rechecked.",
    "sources": {
      "scenario/blender/composer/modal.py": "968819bc3ec818fd5e7afe8ebe801832c66b65556251366da456d2043171a27e",
      "scenario/blender/composer/__init__.py": "9135da55599d3d9a0a63be6e9528571c7cf62b4164fbb55811e3682b9a6b27d6",
      "scenario/blender/composer/state.py": "943d2b3410966c62a00ef7b4a3251a66727f761e5b556e91565ec29d22c50ed4",
      "scenario/blender/operators.py": "59e1e3fb58435b45b40b6bdf06e7f1564dd8b9d1b90c97d71660e9379ee2d296",
      "tests/blender/test_composer.py": "6eadb29d4e7bf1e975e541ad2396768591132876bcea9f4ae268106e4a4ae777",
      "tests/blender/helpers.py": "eb9b1148a436a61479cea0e8f69a02bd18eda96b8c265066ccd3d1ab5ec97ff7"
    }
  }
}
---

# Composer session lifetime after errors and file loads

Supports the [UI style guide](../../UI_STYLE.md#errors-and-file-loads) for how the
floating composer's modal session ends after an error, a removed handler or a file load.
