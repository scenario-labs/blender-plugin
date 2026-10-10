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
    "limits": "Reviewed the user steps against the picker and form code: the Trained chip and its listing order, the first-time base description reads with a progress line, row notes naming the bases, greyed rows with reasons, Runs with and Run with, the bounded strength starting at 1 without a declared default, stacking, re-choosing to change a strength, composition replacement and the effect line, the Model row list with remove buttons, repricing on each change, the quote's fresh reads refusing deleted, inaccessible, retyped or untrained models before any price (trained_routes.check_references, unchanged), choices bound to the credentials and project that made them, and Reload parameters restoring still-listed LoRAs or a composition and clearing others. The chip-list sentence in the Model bullet now includes Trained. The installed suite on macOS arm64 Blender 5.1.2 passed 1,228 tests (2 Windows-only skips), including tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "scenario/blender/model_picker.py": "6d2bef3f5c8f2ccd332650a74e3af6c55e98883547c1e5c9a2f21842e270dc83",
      "scenario/blender/trained_models.py": "e89a939b4d50f4f99566ff696a89217258b8e2edf12585234bfd56bf8a9fd0c8",
      "scenario/blender/operators.py": "525559c86b211d97beb4e2de5fe33bae5b2cfc11ffa45ea7f1b65f842bf17238",
      "scenario/blender/generation.py": "0ef151c8b1ca1e241fdaca1b6566d00c684ecbaf624f564191445488af8fbf57",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/trained_offers.py": "3f26bf5fc4de7b66004722e90aa257e364b4d740637730fd9600682302cdf339",
      "tests/blender/test_trained_models.py": "fbf02e4ac6d78562b429ff70c05c41b6973034b24c269bac822fe7258904416a"
    }
  }
}
---

Evidence for [use a LoRA or composition](../../USER_GUIDE.md#use-a-lora-or-composition).
