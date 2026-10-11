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
    "limits": "Source-reviewed composer input-method handling. Upstream Blender source read from the release tags (not part of this repository) was inspected for the input-method claims: GHOST_WindowViewCocoa.hh, interface_handlers.cc and rna_wm.cc at 5.0.1, 5.1.2 and 5.2.1, and wm_window.cc, wm_event_system.cc and bpy_rna.cc at 5.1.2 only; a background Blender 5.1.2 probe listed the Event properties, the Event type enum and the Window functions: bpy.types.Event exposes no composition data and its type enum omits Blender's IME composite events and unknown keys, so reading such a type returns an empty string with a logged warning; Python has no call that turns input-method composition on, which only native text editing does; on macOS, ending a text edit ends input-method state only when that edit received a composition event, so a later input-source change can route keys to the input method with no field editing (the viewport-shortcut consequence is inferred from that code, not observed); and in 5.1.2 and 5.2.1 a native text field that starts while a composition is pending inserts it on a click outside (5.0.1 has no such insertion). The physical Blender 5.1.2 macOS report that motivated this change logged the composer modal receiving event type values 22, 24 and 25 (IME composite start, event and end) and 171 (unknown key), and a Cube renamed with pending composition text. In the extension, a press with an empty type and no text in the focused prompt, or F2 there, opens a native popover field whose confirmed text is typed at the caret. Installed native tests in tests/blender/test_composer_text_input.py drive the composer modal with synthetic events, stub wm.call_panel and draw the panel into a recording layout, on Blender 5.1.2 macOS arm64 only. No physical input-method composition, candidate-window placement, focus return after the popover, Windows or Linux input method, or Blender 5.0/5.2 native run of this change is claimed; physical acceptance stays under #66.",
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

# Composer input-method limits

Supports [the canonical document](../../KNOWN_LIMITATIONS.md) for the composer's input-method (IME) limit, its native text field and the inspected Blender macOS input-method state.
