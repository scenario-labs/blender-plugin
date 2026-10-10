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
    "limits": "Reviewed the appended tab and its saved index, the segmented mode control drawn with equal_segments, the section order, the mode-restricted picker and dropdown, the GPT size dropdown, greyed contract settings and their note, the LDR and HDR result lines, the panorama input header and sources, the remedy line for captures, the Use saved panorama dialog, the saved-job 360 labels and Make HDRI prefill, and the composer tab behavior. Mode, size and model changes run in property callbacks or operators; drawing reads state only. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover read-only drawing of every mode, the tab values through a saved blend, the picker, Quick settings, Reload and the composer tab. Physical desktop interaction (mouse, keyboard, composer text entry, other scales and window sizes, viewport return) is pending and no Environment screenshot is claimed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Gate re-review: the composer's Settings chip now commits focused text to its original form before Quick settings opens (a changed form refuses and keeps both texts), so an Environment mode change in that dialog cannot move the text to Image, and Make HDRI and Reload relist the target mode's models through select_panorama_mode even when the scene already shows that mode; installed tests cover both, and each fails when its fix is removed.",
    "sources": {
      "docs/UI_STYLE.md": "98b894f16705938c090416de03d91304505cb47c1b905875fe00d9871b24aa91",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "d6c25753c641a863e99920e980ec4e14ead175b5f44c8d7725b7f454c51f3a52",
      "scenario/blender/generation.py": "7fd6bfde60cb2d5ffa758d85fe55ee2c0c582864991e88d2dd79e4d150c24c0b",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/panels.py": "fc31581e9276bce9d21dce3e93b4c9d7d2356b229a4145e3e0f55da959ef7251",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/blender/model_picker.py": "938975148eb1a631f8c12831134dd9cdeef5b9f7079e04fa46ef89256a5be387",
      "scenario/blender/operators.py": "d0139c445429e43ed86bd233ddcfa4a850c142c6ecbb90835ec048bfa051d7a6",
      "scenario/blender/composer/state.py": "fd1733a734fef5e60e980845ef1443875d5f08ca2d08a2a5a07d55af7e5bdfb2",
      "scenario/blender/composer/modal.py": "46f72870f6c58068127dcaf263bd2afab7050e693d4d6f18b6d0936d529cc0b1",
      "scenario/core/ui/composer_layout.py": "2a256652f32380d9ebe72c5ca5e45acc4b34787fccab4f840f8223b27fb5d74a",
      "scenario/core/ui/saved_job_actions.py": "923ec72acee64754b948547f69d3b7f0b851c5c8d58a3156dc028e2131fa4756",
      "tests/blender/test_panorama_lane.py": "a556e269ab2ea9817ac51c92177d03e79b1cac826ee941cc88b4a61a99ce3172",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/blender/test_composer.py": "f1834ec8b08b47ce62c772652ede9811277ec35f812d99c1dbbef700022df3fb",
      "tests/unit/test_composer_layout.py": "33c806c20da138fe0e2d4ac48b5d9b336accd82748b8e0f37bc2e7c6825e52c5",
      "tests/unit/test_saved_job_actions.py": "ba376c38aeb9175d967e8447cf3e9a3dcf99d64e54b2fa651fdef782f5681621"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/UI_STYLE.md#environment-lane).
