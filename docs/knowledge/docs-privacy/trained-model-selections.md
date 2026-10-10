---
{
  "type": "Evidence",
  "id": "docs-privacy.trained-model-selections",
  "title": "Trained-model reads, saved choices and private thumbnails",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "trained-model-selections",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the catalog bullet and the stored-data sentences: the automatic catalog load also reads the selected scope's private trained list; the Trained chip of an open picker dialog reads base descriptions, and a list delivered after the dialog closed reads none; ScenarioTrainedSlot saves model ID, name, kind, lane, strength and range in the .blend with an ID property holding reference_form.scope_key of the selected job scope (a SHA256 of the local scope, not a credential), which trained_models.scope_error requires to match before any request; an ID adopted from an earlier version's text field gets the scope selected when it is adopted, or none without a connection; private-record thumbnails are cached under thumbs/scoped/<scope prefix> and need a selected connection, public ones keep the shared cache; thumbnail download failures and unexpected trained-list failures log only the error type. Online gating of thumbnail downloads is unchanged. The installed suite on macOS arm64 Blender 5.1.2 passed 1,233 tests (2 Windows-only skips), including the 18 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "scenario/blender/props.py": "0129dcf9c9a45520f2c0b8b24fa498c49e2244e2417e3d8e8a4866d2ec3ebdbc",
      "scenario/blender/trained_models.py": "b22065b710995723e43a954910245edc7033710a00dceee93e8000c15023b654",
      "scenario/blender/model_picker.py": "5125349af1e9d02202344ed4758824d50404c98397f702a7a7a8f30be2892bef",
      "scenario/blender/reference_form.py": "520583bf3399a0f79a880f027a5beb61de9dd0eea83c89f9d7500c17b80b4d13",
      "scenario/core/jobs/manager.py": "3f63861575bde2e83b74ab3e8982215432b72615f9b00ba220bb3da3673c3080",
      "tests/blender/test_trained_models.py": "cdc0dad13557080489a7b8957cf6dd2ab73f1dd534c90460650fa5d1b4458f9d",
      "tests/blender/package_update.py": "534d3011b7c48f01fa5f71c0f201b83760b78d6c8342bc9d34b15aebead914a3"
    }
  }
}
---

Evidence for [the canonical document](../../PRIVACY.md).
