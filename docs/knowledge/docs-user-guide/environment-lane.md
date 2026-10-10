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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the Environment tab is appended to the Audio and Materials row and lists only verified contract models per mode (Generate: Flux and GPT; From image: HY World; HDRI; Upscale), that Flux defaults to one output, GPT offers only its three 2:1 presets, HDRI outputs are fixed and drawn greyed, and the upscale factor is capped at 2 for saved results and by the measured size for checked files; that panorama inputs take Saved panorama (downloaded, server-declared 360 results of the selected scope) or a local 2:1 PNG or JPEG checked before a byte-bound upload, never captures or other saved uploads; that results stay saved with no import or World change; that saved-job rows show the 360 label, Set panorama as World and Make HDRI, which only prefills the HDRI form; and that the composer's Environment tab drives the Generate mode. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover the form, request, picker, reload, composer, upload preflight and fake-service submission, restart, Make HDRI and World approval. Physical desktop interaction (mouse, keyboard, composer text entry, other scales and window sizes, viewport return) is pending and no Environment screenshot is claimed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Gate re-review: the composer's Settings chip saves focused text to its own lane before the dialog opens, so an Environment mode change there never moves that text to Image; an installed composer test covers it.",
    "sources": {
      "docs/USER_GUIDE.md": "ad0b6097826cd24395d3c7127d00d24b9b2a61eec02e0ef312f19dd5e2f71dba",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "d6c25753c641a863e99920e980ec4e14ead175b5f44c8d7725b7f454c51f3a52",
      "scenario/blender/generation.py": "7fd6bfde60cb2d5ffa758d85fe55ee2c0c582864991e88d2dd79e4d150c24c0b",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/panels.py": "fc31581e9276bce9d21dce3e93b4c9d7d2356b229a4145e3e0f55da959ef7251",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/core/ui/saved_job_actions.py": "923ec72acee64754b948547f69d3b7f0b851c5c8d58a3156dc028e2131fa4756",
      "scenario/core/ui/composer_layout.py": "2a256652f32380d9ebe72c5ca5e45acc4b34787fccab4f840f8223b27fb5d74a",
      "scenario/blender/composer/state.py": "fd1733a734fef5e60e980845ef1443875d5f08ca2d08a2a5a07d55af7e5bdfb2",
      "tests/blender/test_panorama_lane.py": "a556e269ab2ea9817ac51c92177d03e79b1cac826ee941cc88b4a61a99ce3172",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/unit/test_docs.py": "a8352a16f4caa43264cd87e1ea6cb616ab16c222bd760086f7594a6589184fb8",
      "scenario/blender/composer/modal.py": "46f72870f6c58068127dcaf263bd2afab7050e693d4d6f18b6d0936d529cc0b1",
      "tests/blender/test_composer.py": "f1834ec8b08b47ce62c772652ede9811277ec35f812d99c1dbbef700022df3fb"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/USER_GUIDE.md#environment).
