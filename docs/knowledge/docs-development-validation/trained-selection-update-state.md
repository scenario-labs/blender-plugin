---
{
  "type": "Evidence",
  "id": "docs-development-validation.trained-selection-update-state",
  "title": "Saved trained-model choices across native updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "trained-selection-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed the package probe's trained_lane detection by RNA property, seed_trained (two LoRAs with ranges and strengths, a Unicode name, the selected scope tag), trained_snapshot (IDs, names, kinds, lanes, rounded strengths, ranges, scope tags; accepted for the selected store and refused for the other credential scope), the same refusal for the default scope and another project in check_project_scope, the trained_selection_preserved report field and the runner's expectation from expected-state.json (absent key means false). Unit tests cover the runner with seeded and unseeded choices and false or unsupported claims. Re-reviewed on 2026-10-12 after rebasing onto main 72c5340c: the probe and runner keep these checks beside main's workflow_uploads_preserved. On macOS arm64 Blender 5.1.2 with candidate ZIP sha256 a912f8868385bf0c305e1e1c731ade5aac10e93ff4963f99b9feea507187d0f5 (its 162 Python files match this change's scenario/ sources; the installed suite passed 1,445 tests with it), tools/test_repository_update.py --test-predecessor passed with a candidate-derived predecessor (trained_selection_preserved true after update and restart, schema 10 to 10, no service request) and with --previous-zip built from main 72c5340c by that commit's tools/build.py (ZIP sha256 bbe9d6de16b1d522690ab0088e1ed089212024c68b08914b9746858941cabe41, its 160 Python files identical to that commit; no trained properties, trained_selection_preserved false, workflow, upload, defaults and project state preserved). Predecessors carry synthetic 0.0.0 version metadata, not published release pairs. The offline probe loads no model description, so adopting an ID an earlier version typed into a model text field (trained_models.adopt_typed) is covered by an installed test, not by the update probe. Blender 5.0, 5.2, Linux and Windows were not run.",
    "sources": {
      "tests/blender/package_update.py": "d66fb1ca629b1628acdddae977471960e59b452f8e907086600644cb62d131ee",
      "tools/test_repository_update.py": "a5956fadf8e78ecbe96280b0462cee3f3e72d67974ed87af2ef1b865bae44c09",
      "tests/unit/test_repository_update_runner.py": "601692f8426224f6469dec8ab354b7bcff0d09d77b6965a388d0b525935a249d",
      "scenario/blender/props.py": "8278a907139f11d25faf9bf80f099e5c61a82bce66b331d898eeb59847d4c3f9",
      "scenario/blender/trained_models.py": "b22065b710995723e43a954910245edc7033710a00dceee93e8000c15023b654"
    }
  }
}
---

Evidence for [the canonical document](../../development/validation.md).
