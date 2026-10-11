---
{
  "type": "Evidence",
  "id": "docs-ui-style.composer-input-methods",
  "title": "Composer text input through a native field",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "composer-input-methods",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Source-reviewed the Composer text input section and its line under What Blender cannot do: the modal reads each event's type once before its other handling and handles an empty type without reading it again; without focus it passes through, during a placement drag or on release it is consumed, a press carrying text is typed at the caret unless Ctrl, Cmd or Alt is held, a key repeat is consumed without counting, and the second text-less press in a row opens the popover (the ComposerState untyped_press flag, cleared by any named press, a click included, a release, a drag, an untyped event without focus, a text-carrying press, the popover's opening and the modal's finish). Every untyped press also resets the ComposerState presses double-click pairing, as named key presses already do, so a dead key or composition press between two clicks leaves two plain presses. F2 in the focused prompt opens the same popover. The panel labels the current composer tab, sets activate_init on the row holding the window-manager property, draws a dimmed hint and changes nothing while drawing; the property's update callback types confirmed text through ComposerState.type_text and empties the property. The select-all-on-edit claim (5.0.1, 5.1.2 and 5.2.1), the pending-composition insertion on an outside click (5.1.2 and 5.2.1 only), the start-then-update order of a composition, the absent repeat flag on input-method events, the dead key's text-less unknown-key press and release, and the commit-per-key result travelling in the second press come from upstream source. Upstream Blender source read from the release tags (not part of this repository) was inspected: GHOST_WindowViewCocoa.hh, interface_handlers.cc and rna_wm.cc at 5.0.1, 5.1.2 and 5.2.1; GHOST_SystemCocoa.mm and wm_event_system.cc at 5.1.2, with their dead-key and event-flag code also checked at 5.0.1 and 5.2.1; wm_window.cc and bpy_rna.cc at 5.1.2 only. Installed native tests in tests/blender/test_composer_text_input.py drive the composer modal with synthetic untyped, dead-key, text-carrying and F2 events, stub wm.call_panel and draw the panel into a recording layout; a test in tests/blender/test_composer.py sends a dead key between two pinned-time clicks on the prompt, a click between two untyped presses and a modal finish between presses, and fails without either reset. Both ran on Blender 5.1.2 macOS arm64 only. No physical input-method composition, dead-key typing, commit-per-key first-character loss, candidate-window placement, focus return after the popover, Windows or Linux input method, or Blender 5.0/5.2 native run of this change is claimed; physical acceptance stays under #66.",
    "sources": {
      "scenario/blender/composer/__init__.py": "06a15107991bcdc9f1128739900a1531d50e74a3d591a38400ab8536b3223006",
      "scenario/blender/composer/modal.py": "25f46e05c49822b0c11dbd399f26467e4ee335a7b1e5c0fdbad9481e49ab0218",
      "scenario/blender/composer/state.py": "82001503d91aaa5c8eba2967921c639145dc4d3a1682eb35e4b819f03ebfc3ed",
      "scenario/blender/composer/text_field.py": "1d44b3619a703fca7b5a2b4ba83b720f46d328a4a9ba959f6ffc32067e48a73d",
      "tests/blender/test_composer.py": "e38dd5f53622c32eb71712e5acfeecc2de9a44466909dd089459f4173d952c8f",
      "tests/blender/test_composer_text_input.py": "c3b4316383e5b159f6dad6f315652eaafde4ee83110c70ff6e47d4339b70f5c5"
    }
  }
}
---

# Composer text input through a native field

Supports [the canonical document](../../UI_STYLE.md#composer-text-input) for how the floating composer hands input-method text to a native Blender text field.
