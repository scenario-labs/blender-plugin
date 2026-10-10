---
{
  "type": "Evidence",
  "id": "docs-development-validation.trained-selection-update-state",
  "title": "Saved trained-model choices across native updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "trained-selection-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the package probe's trained_lane detection by RNA property, seed_trained (two LoRAs with ranges and strengths, a Unicode name, the selected scope tag), trained_snapshot (IDs, names, kinds, lanes, rounded strengths, ranges, scope tags; accepted for the selected store and refused for the other credential scope), the same refusal for the default scope and another project in check_project_scope, the trained_selection_preserved report field and the runner's expectation from expected-state.json (absent key means false). Unit tests cover the runner with seeded and unseeded choices and false or unsupported claims. On macOS arm64 Blender 5.1.2 with candidate ZIP sha256 c0a3826082f8e14cfcd04fb37e7d0544b87b625c7b19d130012ba88b5272df9c, tools/test_repository_update.py --test-predecessor passed with a candidate-derived predecessor (trained_selection_preserved true after update and restart, schema 10 to 10) and with a predecessor built from the parent integration commit 03097a35 (ZIP sha256 fc130f6cf6809ab3e3550e3f07fc74cdb09f1823009719798f8e7b9bd67abaf7; no trained properties, trained_selection_preserved false, all other state preserved). Predecessors carry synthetic 0.0.0 version metadata, not published release pairs. Blender 5.0, 5.2, Linux and Windows were not run.",
    "sources": {
      "tests/blender/package_update.py": "534d3011b7c48f01fa5f71c0f201b83760b78d6c8342bc9d34b15aebead914a3",
      "tools/test_repository_update.py": "77ae42bf380481c81694c8c24b0dd509cbc66adb61cd7554b2b2906654de9219",
      "tests/unit/test_repository_update_runner.py": "870745d1536d41766a300cef4eada2a79580a4fa8ecdf3047f2159ca318fffba",
      "scenario/blender/props.py": "0129dcf9c9a45520f2c0b8b24fa498c49e2244e2417e3d8e8a4866d2ec3ebdbc",
      "scenario/blender/trained_models.py": "e89a939b4d50f4f99566ff696a89217258b8e2edf12585234bfd56bf8a9fd0c8"
    }
  }
}
---

Evidence for [the canonical document](../../development/validation.md).
