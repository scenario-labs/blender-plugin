---
{
  "type": "Evidence",
  "id": "docs-ui-style.trained-model-picker",
  "title": "Trained models in the model picker",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed the Trained chip as the last Image chip (model_filter), rows built by trained_offers.offers from the selected connection's private trained list then public LoRAs and compositions, available rows first and others greyed with the reasons the section names, private plain custom models omitted, Private LoRA labels, the lane a choice lands in (Image, or Render Image from it), base descriptions read only when the chip opens (in lane order, once per connection, progress and stop reason, a refresh only re-allowing failed reads) and never from a trained list delivered after the dialog closed (model_picker.trained_view_open, cleared by the operator's execute and cancel), Runs with or Run with with the form's current base, the only base or a Choose a base model placeholder that OK refuses, the bounded strength field starting at a declared default or the visible value 1, the chosen base and strength kept for the same row when its rows are rebuilt (model_picker._on_highlight names the base again) and started anew for another row or a new dialog, the composition LoRA count, the effect line, replacement rules from trained_offers.merged, the whole selection checked with trained_routes.apply before any form change, price invalidation, the experimental line, the Model row list with remove buttons, LoRA inputs never drawn as text (params_ui), an ID an earlier version saved in the base's model text field adopted as the form's choice when it has none (trained_models.adopt_typed from params_ui.sync_params; its kind and name are filled once the list names it), and blocking reasons from trained_models.apply_to. Drawing reads state only; installed tests compare picker and lane state before and after drawing. Re-reviewed on 2026-10-12 after review and desktop findings: a stopped scan marks only the models it reached as attempted (trained_models.on_bases), so the next Trained chip reads the rest while failed reads still wait for a refresh; the open dialog registers its popup region with studio.track_popup and model_picker.refresh_trained refreshes it through studio.redraw_popups when base reads or the trained list rebuild its rows; the list shows model_picker.list_rows rows (ten, fewer when the window height divided by the system UI scale leaves less than the estimated 19 non-list rows, at least two), an estimate not measured on a desktop; a reopened dialog highlights the form's first trained model because _refilter_trained keeps a highlighted row only when it is a trained row; adopt_typed marks the lane's estimate dirty; Reload parameters (operators.SCENARIO_OT_reload_generation through trained_models.restore) keeps a LoRA saved without a strength without one unless the base declares a default, and counts trained models the base's current LoRA inputs cannot describe (trained_offers.saved_ids) in its warning. The installed suite on macOS arm64 Blender 5.1.2 passed 1,452 tests (3 Windows-only skips), including the 24 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records; the seven tests added for the review and desktop findings failed on the previous head. Strength editing in the sidebar and Studio, project defaults and the composer chip label are not implemented. Blender calling the picker dialog's cancel callback is relied on as for the existing review dialogs; it was not observed on a desktop. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "scenario/blender/model_picker.py": "70e7d37b136034358b1dcc110c2b44736bbfcaff021fcb11d8a7139782354d46",
      "scenario/blender/trained_models.py": "a88fd498fac732f5cc2357159431c9c04e20b347bb700c14a7395a4abd4ce92e",
      "scenario/blender/params_ui.py": "390321d1de6ecc590aa3fb3f2268517c81c6d71f1853880c0d9175edbd9400ef",
      "scenario/blender/props.py": "8278a907139f11d25faf9bf80f099e5c61a82bce66b331d898eeb59847d4c3f9",
      "scenario/blender/generation.py": "fb6af01e954f26b62e725e05ecb92906a4525d5858f78d6e1bfd90ce7aee332e",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/trained_offers.py": "0d9b84d0a9c956ceb7a9f5fe7df2fe6c3a5dbded4d6ef02e78e84c4e3456ac5b",
      "scenario/core/api/trained_routes.py": "71266a1f78c2201b7b871c5b84309f4475331a262ffb461f6f45cf5be4bf261a",
      "tests/blender/test_trained_models.py": "e769078e8769dc375e0b7024b4b5358db08a21f8bbc880f6cf08697a66bf921c",
      "tests/blender/test_model_picker.py": "24fff66a05a2f661f491790cc71f681c35cb210483583af898218987b098df97",
      "tests/unit/test_trained_offers.py": "c2f1e32790186449c44859d49b4a8b0f27483411c4dbcde0f2cff5473e0fe6dd",
      "tests/unit/test_model_filter.py": "cc620c3924104b869d1f430ecc5798f980107ead4092ac17c0ba02ea1521ecfa",
      "scenario/blender/studio.py": "ad78d097072b1827173ff4e444e68fcd1faef18b40e2d0b6abcd738c8a3fb620",
      "scenario/blender/operators.py": "d1b33b342711c0b3cb6a2de1012815b92826ba09973f58d63ce802a4c23b2aeb"
    }
  }
}
---

Evidence for [trained models in the picker](../../UI_STYLE.md#trained-models-in-the-picker).
