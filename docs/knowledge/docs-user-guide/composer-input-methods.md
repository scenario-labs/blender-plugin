---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-input-methods",
  "title": "Composer input-method text",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-input-methods",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed the user guide's input-method paragraph against source: F2 with the prompt focused opens the SCENARIO_PT_composer_text_field popover through wm.call_panel with keep_open false, which Blender places at the pointer; its field edits on display and starts empty; Enter applies it and the update callback types the text at the composer caret (replacing a selection) and commits it to the lane; Esc cancels the field edit, which applies nothing; a second press in a row with no Python type and no text in the focused prompt, which is how a composition starts, opens the same popover, and that consumed second press carries a commit-per-key input mode's first character, which is lost; a dead key's lone untyped press and release open nothing, so the accented key that follows is typed into the prompt. Raw romaji in the composer is from the physical Blender 5.1.2 macOS report and upstream source. Upstream Blender source read from the release tags (not part of this repository) was inspected: GHOST_WindowViewCocoa.hh, interface_handlers.cc and rna_wm.cc at 5.0.1, 5.1.2 and 5.2.1; GHOST_SystemCocoa.mm and wm_event_system.cc at 5.1.2, with their dead-key and event-flag code also checked at 5.0.1 and 5.2.1; wm_window.cc and bpy_rna.cc at 5.1.2 only. The sidebar sentence relies on the existing Prompt row drawing lane_state.prompt with a native property field; this topic did not re-review when the sidebar draws the form. Installed native tests in tests/blender/test_composer_text_input.py drive the composer modal with synthetic untyped, dead-key, text-carrying and F2 events, stub wm.call_panel and draw the panel into a recording layout, on Blender 5.1.2 macOS arm64 only. No physical input-method composition, dead-key typing, commit-per-key first-character loss, candidate-window placement, focus return after the popover, Windows or Linux input method, or Blender 5.0/5.2 native run of this change is claimed; physical acceptance stays under #66. Rechecked after rebasing onto main's composer form ownership (#362) for the sentence on the typing rules: when the form behind the focused prompt was replaced, or its model takes no prompt, modal.refuse_text keeps F2 and a composition's second press from opening the popover, and the popover's update callback adds nothing to either form and reports the reason through runtime.set_message; installed Edit form tests in tests/blender/test_composer.py cover both cases on Blender 5.1.2 macOS arm64.",
    "sources": {
      "scenario/blender/composer/__init__.py": "06a15107991bcdc9f1128739900a1531d50e74a3d591a38400ab8536b3223006",
      "scenario/blender/composer/modal.py": "e15580474b2623703c6cb0fe4f3753b4eefa34ea731246740d5715244b2bb53b",
      "scenario/blender/composer/state.py": "cb95d81f7b301c2f527c7de361c9ef39f864f43f422d566b0abe1fcebc50d982",
      "scenario/blender/composer/text_field.py": "753733d22723b17c601a0ae98b78cfb73a7bb22cfd28acc3e9d37ae17fa32fc6",
      "tests/blender/test_composer.py": "d13e3fee51e3e2a32d2d15666e39ec8b202854a6f023794fc1836b5180d02ab7",
      "tests/blender/test_composer_text_input.py": "9058c7f3334511f05da4b4b93407d8e96a4a62c60b1fc890b1c5dea5bc5d7eca"
    }
  }
}
---

# Composer input-method text

Supports [the canonical document](../../USER_GUIDE.md#the-floating-composer) for typing with an input method into the floating composer through Blender's own text field.
