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
    "base_revision": "f68a8175b000b6a3d13975d5f8d5b45ac376a8bc",
    "limits": "Reviewed the user steps against the picker and form code: the Trained chip and its listing order, the first-time base description reads with a progress line, row notes naming the bases, greyed rows with reasons, Runs with and Run with, the bounded strength starting at the LoRA's own declared strength or else 0.75 within the base's range, with a reset returning to that start, stacking, re-choosing to change a strength, composition replacement and the effect line, the Model row list with remove buttons, repricing on each change, the quote's fresh reads refusing deleted, inaccessible, retyped or untrained models before any price (trained_routes.check_references, unchanged), choices bound to the credentials and project that made them, Reload parameters restoring still-listed LoRAs or a composition and clearing others, and a composition ID typed into LoRA or Composition Model with an earlier version appearing as the form's choice with its remove button (trained_models.adopt_typed from params_ui.sync_params, checked like any other choice). The chip-list sentence in the Model bullet now includes Trained. Re-reviewed on 2026-10-12 the Reload parameters sentence: it warns with the number of trained models it could not restore (still unlisted, or no longer described by the base's LoRA inputs, counted with trained_offers.saved_ids) and leaves a LoRA saved without a strength without one, so the price asks for it unless the base declares a default (trained_models.restore). At the review-fix head before the rebase, the installed suite on macOS arm64 Blender 5.1.2 passed 1,452 tests (3 Windows-only skips), and the seven tests added for the review and desktop findings failed on the head before those fixes. Re-reviewed on 2026-10-12 after rebasing onto main f68a8175, whose only change to these sources is generation.py passing schema.exclusive to validate, which leaves these claims unchanged, and after the maintainer chose to match the Scenario web app's starting strength. The strength sentence was checked against trained_offers.strength and declared_strength (the first concepts entry's scale on the listed record, else 0.75, clamped to the base's range) and model_picker's STRENGTH_RESET handling. The installed suite on macOS arm64 Blender 5.1.2 then passed 1,581 tests (3 Windows-only skips), including the 27 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records; with only the new and updated tests copied onto the rebased head before the strength change, the suite failed exactly those five tests (failures=4, errors=1). No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "scenario/blender/model_picker.py": "aef01f35d43854d944eab39f39d98d852b0871f9da368e145ebf557045c66a65",
      "scenario/blender/trained_models.py": "d68ac8a30b120adb118da0fd4fbbdcf5acc9ac35faa476d1200a6f54ea08cc61",
      "scenario/blender/params_ui.py": "390321d1de6ecc590aa3fb3f2268517c81c6d71f1853880c0d9175edbd9400ef",
      "scenario/blender/operators.py": "d1b33b342711c0b3cb6a2de1012815b92826ba09973f58d63ce802a4c23b2aeb",
      "scenario/blender/generation.py": "10f1196ced42b974e461617bdc94c47cd3f0ce2d86ba519cb8817127636626da",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/trained_offers.py": "ba5b85359f85a2b4b6bdc3741b1ecc3403cfcb18b0775a5cc7b1b83d4e073601",
      "tests/blender/test_trained_models.py": "4ad6db5c2276d8217a855f6703c8881d53d42fcef0bceafaf6f48fc7d4751848"
    }
  }
}
---

Evidence for [use a LoRA or composition](../../USER_GUIDE.md#use-a-lora-or-composition).
