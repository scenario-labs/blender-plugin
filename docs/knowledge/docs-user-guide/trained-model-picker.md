---
{
  "type": "Evidence",
  "id": "docs-user-guide.trained-model-picker",
  "title": "Use a LoRA or composition",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed the user steps against the picker and form code: the Trained chip and its listing order, the first-time base description reads with a progress line, row notes naming the bases, greyed rows with reasons, Runs with and Run with, the bounded strength starting at 1 without a declared default, stacking, re-choosing to change a strength, composition replacement and the effect line, the Model row list with remove buttons, repricing on each change, the quote's fresh reads refusing deleted, inaccessible, retyped or untrained models before any price (trained_routes.check_references, unchanged), choices bound to the credentials and project that made them, Reload parameters restoring still-listed LoRAs or a composition and clearing others, and a composition ID typed into LoRA or Composition Model with an earlier version appearing as the form's choice with its remove button (trained_models.adopt_typed from params_ui.sync_params, checked like any other choice). The chip-list sentence in the Model bullet now includes Trained. Re-reviewed on 2026-10-12 the Reload parameters sentence: it warns with the number of trained models it could not restore (still unlisted, or no longer described by the base's LoRA inputs, counted with trained_offers.saved_ids) and leaves a LoRA saved without a strength without one, so the price asks for it unless the base declares a default (trained_models.restore). The installed suite on macOS arm64 Blender 5.1.2 passed 1,452 tests (3 Windows-only skips), including the 24 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records; the seven tests added for the review and desktop findings failed on the previous head. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "scenario/blender/model_picker.py": "70e7d37b136034358b1dcc110c2b44736bbfcaff021fcb11d8a7139782354d46",
      "scenario/blender/trained_models.py": "a88fd498fac732f5cc2357159431c9c04e20b347bb700c14a7395a4abd4ce92e",
      "scenario/blender/params_ui.py": "390321d1de6ecc590aa3fb3f2268517c81c6d71f1853880c0d9175edbd9400ef",
      "scenario/blender/operators.py": "d1b33b342711c0b3cb6a2de1012815b92826ba09973f58d63ce802a4c23b2aeb",
      "scenario/blender/generation.py": "fb6af01e954f26b62e725e05ecb92906a4525d5858f78d6e1bfd90ce7aee332e",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/trained_offers.py": "0d9b84d0a9c956ceb7a9f5fe7df2fe6c3a5dbded4d6ef02e78e84c4e3456ac5b",
      "tests/blender/test_trained_models.py": "e769078e8769dc375e0b7024b4b5358db08a21f8bbc880f6cf08697a66bf921c"
    }
  }
}
---

Evidence for [use a LoRA or composition](../../USER_GUIDE.md#use-a-lora-or-composition).
