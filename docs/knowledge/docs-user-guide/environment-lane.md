---
{
  "type": "Evidence",
  "id": "docs-user-guide.environment-lane",
  "title": "Environment lane user workflow",
  "description": "Generating 360 panoramas, HDRIs and upscales from the native Environment tab.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that the Environment tab is appended to the Audio and Materials row and lists only verified contract models per mode (Generate: Flux and GPT; From image: HY World; HDRI; Upscale), that Flux defaults to one output, GPT offers only its three 2:1 presets, HDRI outputs are fixed and drawn greyed, and the upscale factor is capped at 2 for saved results and by the measured size for checked files; that panorama inputs take Saved panorama (downloaded, server-declared 360 results of the selected scope) or a local 2:1 PNG or JPEG checked before a byte-bound upload, never captures or other saved uploads; that results stay saved with no import or World change; that saved-job rows show the 360 label, Set panorama as World and Make HDRI, which only prefills the HDRI form; and that the composer's Environment tab drives the Generate mode. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover the form, request, picker, reload, composer, upload preflight and fake-service submission, restart, Make HDRI and World approval. A physical macOS arm64 Blender 5.1.2 pass at UI scales 1 and 2, on the exact packaged ZIP of this stack before it was rebased onto #394 and with free quotes only, checked the tab and modes in the sidebar and Studio, the mode-restricted dropdown and picker, settings and result lines, the upscale cap message, PNG, OpenEXR and JPEG World application, Restore previous World, reapplying after a Blender undo, Esc and viewport keys after each dialog, and readability at scale 2; it found material maps offered as World panoramas, which the rebased lane no longer offers through #394's World candidates (installed test, not rechecked physically). The label-sized composer tab row, a local file through Upload reference and From image beyond its quote were not exercised physically, and no screenshot is committed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): Settings saving focused text to its own lane before the dialog opens is main's behavior for every tab, and an installed composer test checks it for an Environment mode change; a narrow card shortens every tab label but 3D, so the guide lists Image to Img and Video to Vid beside Mat, R-Img, R-Vid and Env: the seven tabs share their row by label length (TAB_WEIGHTS), unit tests at UI scales 1, 2 and 4 keep every short label whole on the minimum card, and an installed draw test reads Img, Vid, 3D, Mat, R-Img, R-Vid and Env there at scale 4; material maps are never World, Make HDRI or Use saved panorama choices, and attaching one by ID to the HDRI input is refused with the saved-panorama message while local MCP refuses each one before any dry run (installed test).",
    "sources": {
      "docs/USER_GUIDE.md": "382f786c5c8d54fd5c3d9a6eed164069ab50945b85a1eb4eb5d23d725d7d12d3",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b06289a5193a4345b0dcdfe66a26df8cb362ec856918360deaadedee42d1ff84",
      "scenario/blender/generation.py": "50ad17c4f7bff740bdc8095261835fb3a89ee10cd6c45f16affa3895f09327d2",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/panels.py": "c0cdbf46e8db8e7d400fb4ba6898e497e5da60b082b9e7897619bfd204aa184e",
      "scenario/blender/reference_form.py": "36cb61e5fb31c9efb01b6f7b36b0ff988c08e41bf9ea3985c9d0ef12e9c9cd50",
      "scenario/core/ui/saved_job_actions.py": "54c0728285999c86ba5bb43eb57229ad97b755b66a2ab30441c2f168d59c0e93",
      "scenario/core/ui/composer_layout.py": "4c84afe34242bec6e83a688b7d62125655cd767a6af0c1e25efc21c829fcbae9",
      "scenario/blender/composer/state.py": "48e2abdb7c09ec14ac298a796dd4e186211416f06075143297c46266da37efee",
      "tests/blender/test_panorama_lane.py": "e1371f77d663b68ee782cf6e636ff8b66e32a80a19fb0bfad48931545203f8e8",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/unit/test_docs.py": "a8352a16f4caa43264cd87e1ea6cb616ab16c222bd760086f7594a6589184fb8",
      "scenario/blender/composer/modal.py": "a92c212ac7e8475ef9bf00ead177e68d1fe8605718be71b8477710496e80c2bf",
      "tests/blender/test_composer.py": "300ecb578e9fe9228e1c10695576d2aa87cca3ddbefebd7fee2f9ede466da869",
      "scenario/blender/model_jobs.py": "4eeac905c9f752274d21fcd732d10fde0ffbba950d9c3ec90227ce5a39860f78"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/USER_GUIDE.md#environment).
