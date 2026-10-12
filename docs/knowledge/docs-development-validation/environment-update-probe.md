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
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that the package probe sets the seeded scene's tab to Blockout and includes it in the scene snapshot, seeds a second scene with the Environment tab, HDRI mode, 3072 x 1536 size, prompt, model choice and a saved panorama reference with its markers only when the predecessor's LANE_ITEMS include the lane, reports environment_lane_preserved, and that the runner requires it exactly when expected-state.json contains that state. Unit tests cover absent, preserved and lost reports. On macOS arm64 Blender 5.1.2 the probe passed with a candidate-derived predecessor (Environment preserved through update and offline restart) and with the parent branch's ZIP as predecessor (Environment false, Blockout tab preserved), and a candidate ZIP mutated to insert the tab before Blockout failed with a changed scene state. This is synthetic version evidence, not published release-pair acceptance; Linux and Windows CI and Blender 5.0 and 5.2 runs were not observed here. Gate re-review: the Environment scene also seeds a checked-upload reference with its measured 2:1 size marker (_scenario_reference_panorama) beside upload, scope, request, asset and kind markers; the candidate-derived and parent-ZIP probes were rerun on macOS arm64 Blender 5.1.2 with this seed. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): the runner now requires environment_lane_preserved beside main's workflow_uploads_preserved and model_defaults_preserved, and its unit test crosses the absent, preserved and lost Environment cases with the lane-defaults owner cases; seed_lanes and environment_snapshot are unchanged. With the restacked candidate ZIP (the stack top's exact packaged ZIP) the candidate-derived probe passed on macOS arm64 Blender 5.1.2 with environment_lane_preserved, workflow_uploads_preserved and model_defaults_preserved true after update and offline restart and the normal profile unchanged; the parent-ZIP and mutated-ZIP probes were not rerun after the restack.",
    "sources": {
      "docs/development/validation.md": "b62fa0aac54849e2fac9b8eb4008966fc185ba2ebee60f00348a5c5f20fbe9b3",
      "tests/blender/package_update.py": "e65145c69522953e5545eab55fbca85d4e93b8c3a02b4b25bfaaf34351a76e4e",
      "tools/test_repository_update.py": "f0340de2d493745af0e37100c1386e26d4c0e7cec14e3d6a7a148e246384a3b0",
      "tests/unit/test_repository_update_runner.py": "779f066ba1d1a3640b153f7b57dec3f6aef1d5308fe85062f7f023faf29a748b",
      "scenario/blender/props.py": "b06289a5193a4345b0dcdfe66a26df8cb362ec856918360deaadedee42d1ff84"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/development/validation.md#scenario-package-state-across-updates).
