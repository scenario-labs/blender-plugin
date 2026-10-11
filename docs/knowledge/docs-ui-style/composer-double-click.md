---
{
  "type": "Evidence",
  "id": "docs-ui-style.composer-double-click",
  "title": "Composer double-click pairing",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "composer-double-click",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Source-reviewed against Blender's window-manager source (wm_event_system.cc) at v5.1.2: wm_event_modalkeymap_begin turns a KM_DBL_CLICK event into KM_PRESS before calling a modal operator's modal callback, unless an operator modal key map matched it, and restores it afterwards; the same conversion is present at v5.0.0, v5.2.0 and main. At v5.1.2, wm_event_is_double_click pairs a press of the same type after a release, strictly within U.dbl_click_time of the previous recorded press and within the drag threshold, and a press detected as a double-click does not update the recorded press, so a fast third press pairs again in Blender; the composer starts over instead. Reviewed the composer's DoubleClick pairing in the pure layout (same hit target, strictly less than preferences.inputs.mouse_double_click_time with a 350 ms fallback, within DRAG_THRESHOLD times the UI scale on each axis, spent after a pair, reset by another key or button press, by a drag that moves the composer, by a press outside it and when the modal finishes) and the modal mapping a paired press to its existing double-click branch: word or whitespace-run selection in the prompt, placement and width reset on the card background or resize corner, nothing more on other controls, and the DOUBLE_CLICK value kept for direct callers. Unit tests cover the pairing limits on both axes, the strict interval, target matching, spending, outside presses, reset and a clock that went backwards. Installed native tests on Blender 5.1.2 macOS arm64 in background mode send the modal two press and release pairs with a pinned clock and Blender's real double-click preference: the prompt word selected and replaced by typing, a caret press without selection past the interval, the placement reset within the time and a 4 px drift and kept past either limit, a key or a drag between the presses, the pill expanding under the pointer, a third quick press, a single Generate submission with the generate operator and its readiness patched, and a direct DOUBLE_CLICK value. Times come from time.monotonic when the composer handles each press, not from event timestamps, which Python events do not expose, so a busy main loop can delay the second press past the interval. A physical Blender 5.1.2 macOS 27.0.1 arm64 session (offline, CGEvent input) before this change found a card background double-click leaving the placement unchanged and a prompt double-click placing the caret without selecting the word, on that build and on the earlier 0.10.0 candidate, while the same driver's double-click opened an Outliner rename. This change has not been physically rechecked; Blender 5.0 and 5.2 native runs, other operating systems, trackpad taps and the job strip tray are not claimed.",
    "sources": {
      "scenario/blender/composer/modal.py": "72554933af0043e7bc7a5e2a402f5720cc6ba6f28cd2420bca6cddbe55f2a8e4",
      "scenario/blender/composer/state.py": "b03073dc712fbb1a5386ba17b9d2c73c0bb6d7d91f2f79cd633a1218296da56f",
      "scenario/core/ui/composer_layout.py": "c624fa1cd59b3fa1180b5b4d5881bd32307744b3e6eb6496903d45b6ca87d66c",
      "tests/blender/test_composer.py": "8e90fb0fcc24aaba0ab68c25975e01b8e1a9f01e44bbfb6b048fd7069b79c9b9",
      "tests/unit/test_composer_layout.py": "97974826a4fd7502ff901e047c0bd38ca3740bcc762815db0bbfc95846dd4895"
    }
  }
}
---

# Composer double-click pairing

Supports the [UI style guide](../../UI_STYLE.md#double-click) for how the floating
composer recognizes double-clicks, which Blender hands its modal operator as plain presses.
