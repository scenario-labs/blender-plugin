---
{
  "type": "Evidence",
  "id": "docs-development-validation.environment-update-probe",
  "title": "Environment lane state across package updates",
  "description": "Update probe seeding of saved lane tabs and the appended Environment lane.",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "environment-update-probe",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "881a93472e0d2b00410c091c27d55d8482e99023",
    "limits": "Reviewed that the package probe sets the seeded scene's tab to Blockout and includes it in the scene snapshot, seeds a second scene with the Environment tab, HDRI mode, 3072 x 1536 size, prompt, model choice and a saved panorama reference with its markers only when the predecessor's LANE_ITEMS include the lane, reports environment_lane_preserved, and that the runner requires it exactly when expected-state.json contains that state. Unit tests cover absent, preserved and lost reports. On macOS arm64 Blender 5.1.2 the probe passed with a candidate-derived predecessor (Environment preserved through update and offline restart) and with the parent branch's ZIP as predecessor (Environment false, Blockout tab preserved), and a candidate ZIP mutated to insert the tab before Blockout failed with a changed scene state. This is synthetic version evidence, not published release-pair acceptance; Linux and Windows CI and Blender 5.0 and 5.2 runs were not observed here. Gate re-review: the Environment scene also seeds a checked-upload reference with its measured 2:1 size marker (_scenario_reference_panorama) beside upload, scope, request, asset and kind markers; the candidate-derived and parent-ZIP probes were rerun on macOS arm64 Blender 5.1.2 with this seed. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): the runner now requires environment_lane_preserved beside main's workflow_uploads_preserved and model_defaults_preserved, and its unit test crosses the absent, preserved and lost Environment cases with the lane-defaults owner cases; seed_lanes and environment_snapshot are unchanged. With the restacked candidate ZIP (the stack top's exact packaged ZIP) the candidate-derived probe passed on macOS arm64 Blender 5.1.2 with environment_lane_preserved, workflow_uploads_preserved and model_defaults_preserved true after update and offline restart and the normal profile unchanged; the parent-ZIP and mutated-ZIP probes were not rerun after the restack. Re-checked 2026-10-12 when the trained-model picker branch was rebased on main 881a9347: seed_lanes and environment_snapshot are unchanged beside the added seed_trained and trained_snapshot, the runner still requires environment_lane_preserved exactly when expected-state.json holds the Environment state, and its unit test keeps the absent, preserved and lost cases. With that branch's candidate ZIP (sha256 91ce0157bc69a504cd329124aa251b1354648e5da133d6aadbaa96da88521a67) the candidate-derived probe passed on macOS arm64 Blender 5.1.2 with environment_lane_preserved true after update and offline restart; the parent-ZIP and mutated-ZIP probes were not rerun.",
    "sources": {
      "docs/development/validation.md": "867490c6fb88390e0d5673def77b8bb3e20915c5416a17fb9a4076d66aac7343",
      "tests/blender/package_update.py": "da1ab37cb519ecbe094f5d7d8300ec6d1cd938c628cffd5f662f947a8937a73c",
      "tools/test_repository_update.py": "66b853ded4a0e380f897427f2967a96346b8147e8ed2759f56a1ccd61e0fc6e3",
      "tests/unit/test_repository_update_runner.py": "5c362f4446ef697ad1e0dcdbdb4c0420f81126a09d038898934876e909bea982",
      "scenario/blender/props.py": "7ced8a89caac513ffe38f91d49741882257be0898368f2c28a9ee7e9f86c7af5"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/development/validation.md#scenario-package-state-across-updates).
