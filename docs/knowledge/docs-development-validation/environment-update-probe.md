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
    "limits": "Reviewed that the package probe sets the seeded scene's tab to Blockout and includes it in the scene snapshot, seeds a second scene with the Environment tab, HDRI mode, 3072 x 1536 size, prompt, model choice and a saved panorama reference with its markers only when the predecessor's LANE_ITEMS include the lane, reports environment_lane_preserved, and that the runner requires it exactly when expected-state.json contains that state. Unit tests cover absent, preserved and lost reports. On macOS arm64 Blender 5.1.2 the probe passed with a candidate-derived predecessor (Environment preserved through update and offline restart) and with the parent branch's ZIP as predecessor (Environment false, Blockout tab preserved), and a candidate ZIP mutated to insert the tab before Blockout failed with a changed scene state. This is synthetic version evidence, not published release-pair acceptance; Linux and Windows CI and Blender 5.0 and 5.2 runs were not observed here. Gate re-review: the Environment scene also seeds a checked-upload reference with its measured 2:1 size marker (_scenario_reference_panorama) beside upload, scope, request, asset and kind markers; the candidate-derived and parent-ZIP probes were rerun on macOS arm64 Blender 5.1.2 with this seed.",
    "sources": {
      "docs/development/validation.md": "71dd3e5d9cd1096995bae451a2298dec965589d45e21f147c63da537437bb40a",
      "tests/blender/package_update.py": "df923548fec622eaa9a8de8d62605002fe3aaba86a1ed37b2058c584e8861472",
      "tools/test_repository_update.py": "6f7043c75fd14695573bca0bf75aa27e5bb59678f1e084639e72857e8b7730bf",
      "tests/unit/test_repository_update_runner.py": "9d830dd7f238d95e396796fcfee4e6348d46d47a81ff51df1ddcd8af7c08ff67",
      "scenario/blender/props.py": "d6c25753c641a863e99920e980ec4e14ead175b5f44c8d7725b7f454c51f3a52"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/development/validation.md#scenario-package-state-across-updates).
