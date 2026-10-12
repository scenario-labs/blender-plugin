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
    "base_revision": "881a93472e0d2b00410c091c27d55d8482e99023",
    "limits": "Reviewed the package probe's trained_lane detection by RNA property, seed_trained (two LoRAs with ranges and strengths, a Unicode name, the selected scope tag), trained_snapshot (IDs, names, kinds, lanes, rounded strengths, ranges, scope tags; accepted for the selected store and refused for the other credential scope), the same refusal for the default scope and another project in check_project_scope, the trained_selection_preserved report field and the runner's expectation from expected-state.json (absent key means false). Unit tests cover the runner with seeded and unseeded choices and false or unsupported claims. Re-reviewed on 2026-10-12 after rebasing onto main 72c5340c: the probe and runner keep these checks beside main's workflow_uploads_preserved. On macOS arm64 Blender 5.1.2 with candidate ZIP sha256 a912f8868385bf0c305e1e1c731ade5aac10e93ff4963f99b9feea507187d0f5 (its 162 Python files match this change's scenario/ sources; the installed suite passed 1,445 tests with it), tools/test_repository_update.py --test-predecessor passed with a candidate-derived predecessor (trained_selection_preserved true after update and restart, schema 10 to 10, no service request) and with --previous-zip built from main 72c5340c by that commit's tools/build.py (ZIP sha256 bbe9d6de16b1d522690ab0088e1ed089212024c68b08914b9746858941cabe41, its 160 Python files identical to that commit; no trained properties, trained_selection_preserved false, workflow, upload, defaults and project state preserved). Predecessors carry synthetic 0.0.0 version metadata, not published release pairs. The offline probe loads no model description, so adopting an ID an earlier version typed into a model text field (trained_models.adopt_typed) is covered by an installed test, not by the update probe. Blender 5.0, 5.2, Linux and Windows were not run. Re-checked 2026-10-12 after rebasing on main 881a9347 (with the Environment lane probe): seed calls seed_lanes and then seed_trained, the snapshot keeps both the environment and trained keys, both reports carry environment_lane_preserved and trained_selection_preserved, and the runner unit test keeps the absent, preserved and lost Environment cases beside the seeded and unseeded trained cases. With the rebased candidate ZIP (sha256 91ce0157bc69a504cd329124aa251b1354648e5da133d6aadbaa96da88521a67) the candidate-derived probe passed on macOS arm64 Blender 5.1.2 with trained_selection_preserved and environment_lane_preserved true after update and offline restart and the normal profile unchanged; the parent-commit predecessor probe was not rerun after the rebase. Re-checked on 2026-10-12 after trained_models.adopt_typed stopped re-arming the price itself, which params_ui.sync_params now does: adoption is still covered by installed tests, not by the update probe.",
    "sources": {
      "tests/blender/package_update.py": "da1ab37cb519ecbe094f5d7d8300ec6d1cd938c628cffd5f662f947a8937a73c",
      "tools/test_repository_update.py": "66b853ded4a0e380f897427f2967a96346b8147e8ed2759f56a1ccd61e0fc6e3",
      "tests/unit/test_repository_update_runner.py": "5c362f4446ef697ad1e0dcdbdb4c0420f81126a09d038898934876e909bea982",
      "scenario/blender/props.py": "7ced8a89caac513ffe38f91d49741882257be0898368f2c28a9ee7e9f86c7af5",
      "scenario/blender/trained_models.py": "e9a79cfa5acb4e334e8f4d62ef4bd3d871fb1aa535824b1068210bb2d6f27983"
    }
  }
}
---

Evidence for [the canonical document](../../development/validation.md).
