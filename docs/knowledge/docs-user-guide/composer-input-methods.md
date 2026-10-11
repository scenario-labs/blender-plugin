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
    "limits": "Reviewed the user guide's input-method paragraph against source: F2 with the prompt focused opens the SCENARIO_PT_composer_text_field popover through wm.call_panel with keep_open false, which Blender places at the pointer; its field edits on display and starts empty; Enter applies it and the update callback types the text at the composer caret (replacing a selection) and commits it to the lane; Esc cancels the field edit, which applies nothing; a second press in a row with no Python type and no text in the focused prompt, which is how a composition starts, opens the same popover, and that consumed second press carries a commit-per-key input mode's first character, which is lost; a dead key's lone untyped press and release open nothing, so the accented key that follows is typed into the prompt. Raw romaji in the composer is from the physical Blender 5.1.2 macOS report and upstream source. Upstream Blender source read from the release tags (not part of this repository) was inspected: GHOST_WindowViewCocoa.hh, interface_handlers.cc and rna_wm.cc at 5.0.1, 5.1.2 and 5.2.1; GHOST_SystemCocoa.mm and wm_event_system.cc at 5.1.2, with their dead-key and event-flag code also checked at 5.0.1 and 5.2.1; wm_window.cc and bpy_rna.cc at 5.1.2 only. The sidebar sentence relies on the existing Prompt row drawing lane_state.prompt with a native property field; this topic did not re-review when the sidebar draws the form. Installed native tests in tests/blender/test_composer_text_input.py drive the composer modal with synthetic untyped, dead-key, text-carrying and F2 events, stub wm.call_panel and draw the panel into a recording layout, on Blender 5.1.2 macOS arm64 only. No physical input-method composition, dead-key typing, commit-per-key first-character loss, candidate-window placement, focus return after the popover, Windows or Linux input method, or Blender 5.0/5.2 native run of this change is claimed; physical acceptance stays under #66.",
    "sources": {
      "scenario/blender/composer/__init__.py": "06a15107991bcdc9f1128739900a1531d50e74a3d591a38400ab8536b3223006",
      "scenario/blender/composer/modal.py": "9f9505787fd51eaf6000bbf3a93499c2cd7c647d62ad6374f662775f6048c67d",
      "scenario/blender/composer/state.py": "52d9adab177e4bc4ca87087cb6155a6ce07a2cc44885b59926cca30943c9acc5",
      "scenario/blender/composer/text_field.py": "1d44b3619a703fca7b5a2b4ba83b720f46d328a4a9ba959f6ffc32067e48a73d",
      "tests/blender/test_composer_text_input.py": "c3b4316383e5b159f6dad6f315652eaafde4ee83110c70ff6e47d4339b70f5c5"
    }
  }
}
---

# Composer input-method text

Supports [the canonical document](../../USER_GUIDE.md#the-floating-composer) for typing with an input method into the floating composer through Blender's own text field.
