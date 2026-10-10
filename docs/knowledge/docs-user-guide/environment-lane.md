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
    "limits": "Reviewed that the Environment tab is appended to the Audio and Materials row and lists only verified contract models per mode (Generate: Flux and GPT; From image: HY World; HDRI; Upscale), that Flux defaults to one output, GPT offers only its three 2:1 presets, HDRI outputs are fixed and drawn greyed, and the upscale factor is capped at 2 for saved results and by the measured size for checked files; that panorama inputs take Saved panorama (downloaded, server-declared 360 results of the selected scope) or a local 2:1 PNG or JPEG checked before a byte-bound upload, never captures or other saved uploads; that results stay saved with no import or World change; that saved-job rows show the 360 label, Set panorama as World and Make HDRI, which only prefills the HDRI form; and that the composer's Environment tab drives the Generate mode. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover the form, request, picker, reload, composer, upload preflight and fake-service submission, restart, Make HDRI and World approval. Physical desktop interaction (mouse, keyboard, composer text entry, other scales and window sizes, viewport return) is pending and no Environment screenshot is claimed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/USER_GUIDE.md": "287dac5fd8d0f49d5a882e6b72772f1b582043b37a9909cf2cb9c84e93e0de66",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b85199b13c0f7fdac0108efc28b39d7e35b0d7fe0b4ac60a39c95020c8d28521",
      "scenario/blender/generation.py": "265c53ce191b2b8d9f0eabecc1f0a726aa5758b0fae958ff1cae9b9aa0d620dd",
      "scenario/blender/panorama_lane.py": "84988f58d11e07b55f00285bcedae5d665324af4d195af9c50342193f4ff6e3b",
      "scenario/blender/panels.py": "fc31581e9276bce9d21dce3e93b4c9d7d2356b229a4145e3e0f55da959ef7251",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/core/ui/saved_job_actions.py": "923ec72acee64754b948547f69d3b7f0b851c5c8d58a3156dc028e2131fa4756",
      "scenario/core/ui/composer_layout.py": "2a256652f32380d9ebe72c5ca5e45acc4b34787fccab4f840f8223b27fb5d74a",
      "scenario/blender/composer/state.py": "fd1733a734fef5e60e980845ef1443875d5f08ca2d08a2a5a07d55af7e5bdfb2",
      "tests/blender/test_panorama_lane.py": "539c48697cad7224d20b2638e6f92d63a83352b52190394f8c6842c7825f5e86",
      "tests/unit/test_panorama_contract.py": "03b45364309d8d1f2c5016966ed794f8f215088e6ed42047b0fdaf62cf53be70",
      "tests/unit/test_docs.py": "a8352a16f4caa43264cd87e1ea6cb616ab16c222bd760086f7594a6589184fb8"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/USER_GUIDE.md#environment).
