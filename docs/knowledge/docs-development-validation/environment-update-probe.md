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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the package probe sets the seeded scene's tab to Blockout and includes it in the scene snapshot, seeds a second scene with the Environment tab, HDRI mode, 3072 x 1536 size, prompt, model choice and a saved panorama reference with its markers only when the predecessor's LANE_ITEMS include the lane, reports environment_lane_preserved, and that the runner requires it exactly when expected-state.json contains that state. Unit tests cover absent, preserved and lost reports. On macOS arm64 Blender 5.1.2 the probe passed with a candidate-derived predecessor (Environment preserved through update and offline restart) and with the parent branch's ZIP as predecessor (Environment false, Blockout tab preserved), and a candidate ZIP mutated to insert the tab before Blockout failed with a changed scene state. This is synthetic version evidence, not published release-pair acceptance; Linux and Windows CI and Blender 5.0 and 5.2 runs were not observed here.",
    "sources": {
      "docs/development/validation.md": "54f2c63d31377938b749f3c7972f47f169eb50c0dad2dc105878f6e5c3e66a02",
      "tests/blender/package_update.py": "19a9b4f243dfac4184a78a0523997dfb04fb532e6eed40dafd1263fed669d3b3",
      "tools/test_repository_update.py": "6f7043c75fd14695573bca0bf75aa27e5bb59678f1e084639e72857e8b7730bf",
      "tests/unit/test_repository_update_runner.py": "9d830dd7f238d95e396796fcfee4e6348d46d47a81ff51df1ddcd8af7c08ff67",
      "scenario/blender/props.py": "b85199b13c0f7fdac0108efc28b39d7e35b0d7fe0b4ac60a39c95020c8d28521"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/development/validation.md#scenario-package-state-across-updates).
