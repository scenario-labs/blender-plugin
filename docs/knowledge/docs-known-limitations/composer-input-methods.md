---
{
  "type": "Evidence",
  "id": "docs-known-limitations.composer-input-methods",
  "title": "Composer input-method limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "composer-input-methods",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Source-reviewed composer input-method handling. Upstream Blender source read from the release tags (not part of this repository) was inspected: GHOST_WindowViewCocoa.hh, interface_handlers.cc and rna_wm.cc at 5.0.1, 5.1.2 and 5.2.1; GHOST_SystemCocoa.mm and wm_event_system.cc at 5.1.2, with their dead-key and event-flag code also checked at 5.0.1 and 5.2.1; wm_window.cc and bpy_rna.cc at 5.1.2 only. bpy.types.Event exposes no composition data and its type enum omits Blender's IME composite events and unknown keys, so reading such a type returns an empty string with a logged warning; Python has no call that turns input-method composition on, which only native text editing does; on macOS, ending a text edit ends input-method state only when that edit received a composition event, so a later input-source change can route keys to the input method with no field editing (the viewport-shortcut consequence is inferred from that code, not observed); in 5.1.2 and 5.2.1 a native text field that starts while a composition is pending inserts it on a click outside (5.0.1 has no such insertion); a composition begins with a start event followed by an update within one key press, and input-method events are presses never flagged as repeats; a dead key arrives as an unknown-key press and release with no text; and in an input mode that commits each key, the first key's result travels in the update event, the second press. A background Blender 5.1.2 probe listed the Event properties, the Event type enum and the Window functions. The physical Blender 5.1.2 macOS report that motivated this change logged the composer modal receiving event type values 22, 24 and 25 (IME composite start, event and end) and 171 (unknown key), and a Cube renamed with pending composition text. In the extension, the focused prompt opens a native popover field on the second press in a row with an empty type and no text; a release, a placement drag, an untyped event without focus or a named or text-carrying press starts the count again, and a key repeat does not count. An untyped key carrying text is typed at the caret without Ctrl, Cmd or Alt, and every untyped event is handled after one read of its type. F2 in the focused prompt opens the same popover, whose confirmed text is typed at the caret. Installed native tests in tests/blender/test_composer_text_input.py drive the composer modal with synthetic untyped, dead-key, text-carrying and F2 events, stub wm.call_panel and draw the panel into a recording layout, on Blender 5.1.2 macOS arm64 only. No physical input-method composition, dead-key typing, commit-per-key first-character loss, candidate-window placement, focus return after the popover, Windows or Linux input method, or Blender 5.0/5.2 native run of this change is claimed; physical acceptance stays under #66.",
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

# Composer input-method limits

Supports [the canonical document](../../KNOWN_LIMITATIONS.md) for the composer's input-method (IME) limit, its native text field and the inspected Blender macOS input-method state.
