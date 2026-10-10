---
{
  "type": "Evidence",
  "id": "docs-user-guide.trained-model-picker",
  "title": "Use a LoRA or composition",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the user steps against the picker and form code: the Trained chip and its listing order, the first-time base description reads with a progress line, row notes naming the bases, greyed rows with reasons, Runs with and Run with, the bounded strength starting at 1 without a declared default, stacking, re-choosing to change a strength, composition replacement and the effect line, the Model row list with remove buttons, repricing on each change, the quote's fresh reads refusing deleted, inaccessible, retyped or untrained models before any price (trained_routes.check_references, unchanged), choices bound to the credentials and project that made them, Reload parameters restoring still-listed LoRAs or a composition and clearing others, and a composition ID typed into LoRA or Composition Model with an earlier version appearing as the form's choice with its remove button (trained_models.adopt_typed from params_ui.sync_params, checked like any other choice). The chip-list sentence in the Model bullet now includes Trained. The installed suite on macOS arm64 Blender 5.1.2 passed 1,233 tests (2 Windows-only skips), including the 18 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "scenario/blender/model_picker.py": "5125349af1e9d02202344ed4758824d50404c98397f702a7a7a8f30be2892bef",
      "scenario/blender/trained_models.py": "b22065b710995723e43a954910245edc7033710a00dceee93e8000c15023b654",
      "scenario/blender/params_ui.py": "7ac18b27559560d4ce7886eefb23978e9a1494fafc925fbf605e30e5a61482af",
      "scenario/blender/operators.py": "525559c86b211d97beb4e2de5fe33bae5b2cfc11ffa45ea7f1b65f842bf17238",
      "scenario/blender/generation.py": "599f62901fc5a23dfcfd12afb862f983435651a52df2faf3e7f579310f05e122",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/trained_offers.py": "3f26bf5fc4de7b66004722e90aa257e364b4d740637730fd9600682302cdf339",
      "tests/blender/test_trained_models.py": "cdc0dad13557080489a7b8957cf6dd2ab73f1dd534c90460650fa5d1b4458f9d"
    }
  }
}
---

Evidence for [use a LoRA or composition](../../USER_GUIDE.md#use-a-lora-or-composition).
