---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-input-methods",
  "title": "Composer input-method text",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-input-methods",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the user guide's input-method paragraph against source: F2 with the prompt focused opens the SCENARIO_PT_composer_text_field popover through wm.call_panel with keep_open false; its field edits on display and starts empty; Enter applies it and the update callback types the text at the composer caret (replacing a selection) and commits it to the lane; Esc cancels the field edit, which applies nothing; a press with no Python type and no text in the focused prompt, which is how composition events reach it, opens the same popover. Raw romaji in the composer is from the physical Blender 5.1.2 macOS report and upstream Blender source read from the release tags (GHOST_WindowViewCocoa.hh and interface_handlers.cc at 5.0.1, 5.1.2 and 5.2.1, wm_window.cc and wm_event_system.cc at 5.1.2; not part of this repository). The sidebar sentence relies on the existing Prompt row drawing lane_state.prompt with a native property field; this topic did not re-review when the sidebar draws the form. Installed native tests in tests/blender/test_composer_text_input.py drive the composer modal with synthetic events, stub wm.call_panel and draw the panel into a recording layout, on Blender 5.1.2 macOS arm64 only. No physical input-method composition, candidate-window placement, focus return after the popover, Windows or Linux input method, or Blender 5.0/5.2 native run of this change is claimed; physical acceptance stays under #66.",
    "sources": {
      "scenario/blender/composer/__init__.py": "06a15107991bcdc9f1128739900a1531d50e74a3d591a38400ab8536b3223006",
      "scenario/blender/composer/modal.py": "e184504b61f81ad4fd60f2f902c57272f7fd54ecf7cc55c597dc6ab444c64b8a",
      "scenario/blender/composer/state.py": "497500c07a1e2d5380c9a3dc52e74b217793dafbd2f94306cb208e01ab155ce9",
      "scenario/blender/composer/text_field.py": "907159dcf6e7d392369510e21befa49a9a8fcaeecc33840cd8f11314ad40bc4e",
      "tests/blender/test_composer_text_input.py": "bade3f184a78b66cc8a995606a3c07c7efe3053f3c0ab30ae25f7992f0b09f78"
    }
  }
}
---

# Composer input-method text

Supports [the canonical document](../../USER_GUIDE.md#the-floating-composer) for typing with an input method into the floating composer through Blender's own text field.
