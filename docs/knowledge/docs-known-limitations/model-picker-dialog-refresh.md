---
{
  "type": "Evidence",
  "id": "docs-known-limitations.model-picker-dialog-refresh",
  "title": "Model picker rebuilds and clicks on OK",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "model-picker-dialog-refresh",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "0d266fa3c1397402686a841f8e979c0a1db9a0ca",
    "limits": "Reviewed the model picker limitation in Interface and capture against the picker and pump code. SCENARIO_OT_pick_model.draw keeps its popup region in model_picker._dialogs, and refresh_dialog tags it with tag_refresh_ui only while the dialog is open: from refresh_trained when the trained list, its failure or a base-description batch arrives, and from refresh_thumbnails, which pump._process calls each tick but which refreshes only after a download worker set _thumbs_arrived; studio.redraw_popups no longer reaches the picker. Blender 5.1.2's source was inspected for the rebuild itself: popup_block_ex creates the dialog with can_refresh, a tagged region recreates the block through popup_block_refresh, OK and Cancel carry the block as their second callback argument in wm_block_dialog_create so ui_but_equals_old never matches them in the rebuilt block, and button_active_free exits an OK that was active (highlighted or pressed) with cancel set, which reports nothing. A click that lands on one of the remaining rebuilds is therefore still lost; ui_do_but_textedit ends a text edit on a press outside the field and consumes it, so a click while a field is edited only ends the edit. A temporary installed probe on macOS arm64 Blender 5.1.2 counted four refreshes of the open picker over four idle pump ticks on the previous code and none with this change; test_pump_ticks_never_rebuild_the_open_dialog_under_its_ok_button checks idle ticks, Studio's per-tick popups, one refresh for cached thumbnails and for a trained-list delivery, and no refresh once the dialog closed, and test_opening_the_picker_downloads_thumbnails_only_with_online_access checks the worker's signal. The full installed suite passed 2,005 tests with 3 Windows-only skips on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Background Blender opens no dialog, so these tests drive the picker's draw and the pump with a recorded region; a physical click on OK, its frequency of loss during scans and thumbnail downloads, other Blender versions on a desktop, other OSes and UI scales are not established and stay with #440. Review follow-up on 2026-10-13: the experimental line now reads Experimental: LoRAs and compositions in testing, so the picker's compositions are named too; refreshed fingerprints this topic had already re-checked. Re-checked on 2026-10-13: test_trained_models.py's only change is the dialog drawing test asserting the picker's single, full experimental line; the refresh tests this topic cites are unchanged. Only that fingerprint is refreshed; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/model_picker.py": "d6aab6af577510662a6fd0219bc0cfdf130766669194f44fb97d95b00a96035e",
      "scenario/blender/pump.py": "5a751724d9c100000d3dabeef7a9190a0ab35cf4cbdc40485f6134f19b9400c8",
      "scenario/blender/studio.py": "41e0e0305bb47e3c82809fdfcddf34a89406198f2745e0009cfde697575b217c",
      "tests/blender/test_trained_models.py": "3009543f6b3ff4a41a1ddc0c4c43b1b967bcb577766632cbb7eaa5fa792b4e86",
      "tests/blender/test_model_picker.py": "87ea96a14d69a87957bf34e3bd8fec3dbf239eb4cb11c44a5ef90df7f8a6535a"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md#interface-and-capture).
