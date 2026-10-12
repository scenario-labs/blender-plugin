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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed the appended tab and its saved index, the segmented mode control drawn with equal_segments, the section order, the mode-restricted picker and dropdown, the GPT size dropdown, greyed contract settings and their note, the LDR and HDR result lines, the panorama input header and sources, the remedy line for captures, the Use saved panorama dialog, the saved-job 360 labels and Make HDRI prefill, and the composer tab behavior. Mode, size and model changes run in property callbacks or operators; drawing reads state only. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover read-only drawing of every mode, the tab values through a saved blend, the picker, Quick settings, Reload and the composer tab. A physical macOS arm64 Blender 5.1.2 pass at UI scales 1 and 2, on the exact packaged ZIP of this stack before it was rebased onto #394 and with free quotes only, checked the tab and modes in the sidebar and Studio, the mode-restricted dropdown and picker, settings and result lines, the upscale cap message, PNG, OpenEXR and JPEG World application, Restore previous World, reapplying after a Blender undo, Esc and viewport keys after each dialog, and readability at scale 2; it found material maps offered as World panoramas, which the rebased lane no longer offers through #394's World candidates (installed test, not rechecked physically). The label-sized composer tab row, a local file through Upload reference and From image beyond its quote were not exercised physically, and no screenshot is committed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): committing focused text before Quick settings opens (a changed form refuses and keeps both texts) is main's composer behavior for every tab, and an installed test checks it for an Environment mode change; Make HDRI and Reload relist the target mode's models through select_panorama_mode even when the scene already shows that mode; the seven composer tabs share their row by label length (TAB_WEIGHTS), so unit tests at UI scales 1, 2 and 4 keep every short label, Env included, whole on the minimum card and every full label on the default card, and an installed draw test reads Img, Vid, 3D, Mat, R-Img, R-Vid and Env on the minimum card at scale 4; contract values and the recorded model key are stored without RNA updates, so a catalog load keeps captured origins (main's catalog-load origin test passes with the lane); the 360 label, Make HDRI and Use saved panorama never offer material maps, and World candidates come from #394's world_assets (installed test).",
    "sources": {
      "docs/UI_STYLE.md": "c677772c56389ae1a082c45ce9a77a33fc2ebe13755818db00a306de7f04dc2c",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b06289a5193a4345b0dcdfe66a26df8cb362ec856918360deaadedee42d1ff84",
      "scenario/blender/generation.py": "50ad17c4f7bff740bdc8095261835fb3a89ee10cd6c45f16affa3895f09327d2",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/panels.py": "c0cdbf46e8db8e7d400fb4ba6898e497e5da60b082b9e7897619bfd204aa184e",
      "scenario/blender/reference_form.py": "36cb61e5fb31c9efb01b6f7b36b0ff988c08e41bf9ea3985c9d0ef12e9c9cd50",
      "scenario/blender/model_picker.py": "938975148eb1a631f8c12831134dd9cdeef5b9f7079e04fa46ef89256a5be387",
      "scenario/blender/operators.py": "b4f7e1f2974b1ca848c3d0e50594658b9708e328a3aaa4132f37fd41484179a0",
      "scenario/blender/composer/state.py": "48e2abdb7c09ec14ac298a796dd4e186211416f06075143297c46266da37efee",
      "scenario/blender/composer/modal.py": "a92c212ac7e8475ef9bf00ead177e68d1fe8605718be71b8477710496e80c2bf",
      "scenario/core/ui/composer_layout.py": "4c84afe34242bec6e83a688b7d62125655cd767a6af0c1e25efc21c829fcbae9",
      "scenario/core/ui/saved_job_actions.py": "ab85bf3e0c7dd17305d7d199daeb17dd6c8d81f7aedae5619cf42cd40a7f1d9f",
      "tests/blender/test_panorama_lane.py": "e1371f77d663b68ee782cf6e636ff8b66e32a80a19fb0bfad48931545203f8e8",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/blender/test_composer.py": "300ecb578e9fe9228e1c10695576d2aa87cca3ddbefebd7fee2f9ede466da869",
      "tests/unit/test_composer_layout.py": "3a2dab00dceffe0bd86cc5c5baebdb16c63f2a2dcbd1fde075fd9d95f91f7de6",
      "tests/unit/test_saved_job_actions.py": "5691a0d860e984d74dab8e4160bcf4cf3942f95899fc690a8f5cc2f3dde36402",
      "scenario/blender/model_jobs.py": "4eeac905c9f752274d21fcd732d10fde0ffbba950d9c3ec90227ce5a39860f78"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/UI_STYLE.md#environment-lane).
