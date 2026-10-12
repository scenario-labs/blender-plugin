---
{
  "type": "Evidence",
  "id": "docs-ui-style.composer-input-methods",
  "title": "Composer text input through a native field",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "composer-input-methods",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Source-reviewed the Composer text input section and its line under What Blender cannot do: the modal reads each event's type once before its other handling and handles an empty type without reading it again; without focus it passes through, during a placement drag or on release it is consumed, a press carrying text is typed at the caret unless Ctrl, Cmd or Alt is held, a key repeat is consumed without counting, and the second text-less press in a row opens the popover (the ComposerState untyped_press flag, cleared by any named press, a click included, a release, a drag, an untyped event without focus, a text-carrying press, the popover's opening and the modal's finish). Every untyped press also resets the ComposerState presses double-click pairing, as named key presses already do, so a dead key or composition press between two clicks leaves two plain presses. F2 in the focused prompt opens the same popover. The panel labels the current composer tab, sets activate_init on the row holding the window-manager property, draws a dimmed hint and changes nothing while drawing; the property's update callback types confirmed text through ComposerState.type_text and empties the property. The select-all-on-edit claim (5.0.1, 5.1.2 and 5.2.1), the pending-composition insertion on an outside click (5.1.2 and 5.2.1 only), the start-then-update order of a composition, the absent repeat flag on input-method events, the dead key's text-less unknown-key press and release, and the commit-per-key result travelling in the second press come from upstream source. Upstream Blender source read from the release tags (not part of this repository) was inspected: GHOST_WindowViewCocoa.hh, interface_handlers.cc and rna_wm.cc at 5.0.1, 5.1.2 and 5.2.1; GHOST_SystemCocoa.mm and wm_event_system.cc at 5.1.2, with their dead-key and event-flag code also checked at 5.0.1 and 5.2.1; wm_window.cc and bpy_rna.cc at 5.1.2 only. Installed native tests in tests/blender/test_composer_text_input.py drive the composer modal with synthetic untyped, dead-key, text-carrying and F2 events, stub wm.call_panel and draw the panel into a recording layout; a test in tests/blender/test_composer.py sends a dead key between two pinned-time clicks on the prompt, a click between two untyped presses and a modal finish between presses, and fails without either reset. Both ran on Blender 5.1.2 macOS arm64 only. No physical input-method composition, dead-key typing, commit-per-key first-character loss, candidate-window placement, focus return after the popover, Windows or Linux input method, or Blender 5.0/5.2 native run of this change is claimed; physical acceptance stays under #66. Rechecked after rebasing onto main's composer form ownership (#362): the untyped key with text, F2 and a composition's second press now pass modal.refuse_text, the rule the named text keys use (a form that replaced the focused prompt's refuses with the Esc warning and keeps focus and the original text; a form whose model takes no prompt leaves focus with This model takes no prompt), and open no popover when refused; the popover's update callback applies the same rule before ComposerState.type_text and reports a refusal through runtime.set_message. ComposerState.sync_from_lane and commit_to_lane now follow the generation lane, so popover text for the 3D tab in Edit mode reaches the Edit 3D prompt; the popover label still names the tab. Installed Edit form tests in tests/blender/test_composer.py send an untyped key with text, F2, a composition's two presses and a popover confirmation to a replaced form and to a prompt-less form; on the rebased branch without this rule they report 8 failures in those 2 tests (the field took the text and the popover opened), and they pass with it. The rebased ZIP ran 1,424 installed tests on macOS arm64 Blender 5.1.2 with every composer test passing.",
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

# Composer text input through a native field

Supports [the canonical document](../../UI_STYLE.md#composer-text-input) for how the floating composer hands input-method text to a native Blender text field.
