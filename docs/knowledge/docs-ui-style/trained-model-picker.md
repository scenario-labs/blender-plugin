---
{
  "type": "Evidence",
  "id": "docs-ui-style.trained-model-picker",
  "title": "Trained models in the model picker",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Trained chip as the last Image chip (model_filter), rows built by trained_offers.offers from the selected connection's private trained list then public LoRAs and compositions, available rows first and others greyed with the reasons the section names, private plain custom models omitted, Private LoRA labels, the lane a choice lands in (Image, or Render Image from it), base descriptions read only when the chip opens (in lane order, once per connection, progress and stop reason, a refresh only re-allowing failed reads) and never from a trained list delivered after the dialog closed (model_picker.trained_view_open, cleared by the operator's execute and cancel), Runs with or Run with with the form's current base, the only base or a Choose a base model placeholder that OK refuses, the bounded strength field starting at a declared default or the visible value 1, the chosen base and strength kept for the same row when its rows are rebuilt (model_picker._on_highlight names the base again) and started anew for another row or a new dialog, the composition LoRA count, the effect line, replacement rules from trained_offers.merged, the whole selection checked with trained_routes.apply before any form change, price invalidation, the experimental line, the Model row list with remove buttons, LoRA inputs never drawn as text (params_ui), an ID an earlier version saved in the base's model text field adopted as the form's choice when it has none (trained_models.adopt_typed from params_ui.sync_params; its kind and name are filled once the list names it), and blocking reasons from trained_models.apply_to. Drawing reads state only; installed tests compare picker and lane state before and after drawing. The installed suite on macOS arm64 Blender 5.1.2 passed 1,233 tests (2 Windows-only skips), including the 18 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records. Strength editing in the sidebar and Studio, project defaults and the composer chip label are not implemented. Blender calling the picker dialog's cancel callback is relied on as for the existing review dialogs; it was not observed on a desktop. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "scenario/blender/model_picker.py": "5125349af1e9d02202344ed4758824d50404c98397f702a7a7a8f30be2892bef",
      "scenario/blender/trained_models.py": "b22065b710995723e43a954910245edc7033710a00dceee93e8000c15023b654",
      "scenario/blender/params_ui.py": "7ac18b27559560d4ce7886eefb23978e9a1494fafc925fbf605e30e5a61482af",
      "scenario/blender/props.py": "0129dcf9c9a45520f2c0b8b24fa498c49e2244e2417e3d8e8a4866d2ec3ebdbc",
      "scenario/blender/generation.py": "599f62901fc5a23dfcfd12afb862f983435651a52df2faf3e7f579310f05e122",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/trained_offers.py": "3f26bf5fc4de7b66004722e90aa257e364b4d740637730fd9600682302cdf339",
      "scenario/core/api/trained_routes.py": "908b49b8b5ecdd8ee5869fe07178b80b9e2d3a385b11d694babaf2515a3f0162",
      "tests/blender/test_trained_models.py": "cdc0dad13557080489a7b8957cf6dd2ab73f1dd534c90460650fa5d1b4458f9d",
      "tests/blender/test_model_picker.py": "b4382d32b2485a2f49b56750acb0e15e3c64c3499e46b6485387338cb1a6b9ee",
      "tests/unit/test_trained_offers.py": "1165fd41f3398f8a229c8da20f2f39381aa1603bf4d2dd4b2255de43162e5df3",
      "tests/unit/test_model_filter.py": "cc620c3924104b869d1f430ecc5798f980107ead4092ac17c0ba02ea1521ecfa"
    }
  }
}
---

Evidence for [trained models in the picker](../../UI_STYLE.md#trained-models-in-the-picker).
