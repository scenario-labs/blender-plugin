---
{
  "type": "Evidence",
  "id": "docs-ui-style.environment-lane",
  "title": "Environment lane presentation",
  "description": "Tab placement, mode control, contract form, panorama inputs and saved-job labels.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the appended tab and its saved index, the segmented mode control drawn with equal_segments, the section order, the mode-restricted picker and dropdown, the GPT size dropdown, greyed contract settings and their note, the LDR and HDR result lines, the panorama input header and sources, the remedy line for captures, the Use saved panorama dialog, the saved-job 360 labels and Make HDRI prefill, and the composer tab behavior. Mode, size and model changes run in property callbacks or operators; drawing reads state only. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover read-only drawing of every mode, the tab values through a saved blend, the picker, Quick settings, Reload and the composer tab. Physical desktop interaction (mouse, keyboard, composer text entry, other scales and window sizes, viewport return) is pending and no Environment screenshot is claimed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/UI_STYLE.md": "d10c4ffd1d3e05c58bf49aca8f4dd6b6611d2da0f1ab25b9ab3e9e40a919353d",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b85199b13c0f7fdac0108efc28b39d7e35b0d7fe0b4ac60a39c95020c8d28521",
      "scenario/blender/generation.py": "265c53ce191b2b8d9f0eabecc1f0a726aa5758b0fae958ff1cae9b9aa0d620dd",
      "scenario/blender/panorama_lane.py": "84988f58d11e07b55f00285bcedae5d665324af4d195af9c50342193f4ff6e3b",
      "scenario/blender/panels.py": "fc31581e9276bce9d21dce3e93b4c9d7d2356b229a4145e3e0f55da959ef7251",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/blender/model_picker.py": "938975148eb1a631f8c12831134dd9cdeef5b9f7079e04fa46ef89256a5be387",
      "scenario/blender/operators.py": "114b6e6f8911969739b9cef634b267925f7c3b0e6ecc2229213c7deb001b3a31",
      "scenario/blender/composer/state.py": "fd1733a734fef5e60e980845ef1443875d5f08ca2d08a2a5a07d55af7e5bdfb2",
      "scenario/blender/composer/modal.py": "bc2800e3d977447461c7e88adff90e42b69b010f9c98c64386f284e15f985785",
      "scenario/core/ui/composer_layout.py": "2a256652f32380d9ebe72c5ca5e45acc4b34787fccab4f840f8223b27fb5d74a",
      "scenario/core/ui/saved_job_actions.py": "923ec72acee64754b948547f69d3b7f0b851c5c8d58a3156dc028e2131fa4756",
      "tests/blender/test_panorama_lane.py": "539c48697cad7224d20b2638e6f92d63a83352b52190394f8c6842c7825f5e86",
      "tests/unit/test_panorama_contract.py": "03b45364309d8d1f2c5016966ed794f8f215088e6ed42047b0fdaf62cf53be70",
      "tests/blender/test_composer.py": "cc2afa5d7415e9f725bfd9a0ee275a44bc0e1b07c999c219f4fb00d903cd85e1",
      "tests/unit/test_composer_layout.py": "33c806c20da138fe0e2d4ac48b5d9b336accd82748b8e0f37bc2e7c6825e52c5",
      "tests/unit/test_saved_job_actions.py": "ba376c38aeb9175d967e8447cf3e9a3dcf99d64e54b2fa651fdef782f5681621"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/UI_STYLE.md#environment-lane).
