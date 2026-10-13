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
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed 2026-10-13 against the current guide text for this topic. Checked: Environment in the sidebar lane list and in What it does (props.LANE_ITEMS, the lane tab rows in panels.py); the composer's Environment tab, which selects and drives the Generate mode, while another sidebar Environment mode makes the composer drive Image (composer_layout.LANE_ORDER, composer/state.py choose_lane and lane_for, the modal tab click); the four modes and their verified contract models (panorama_contract.CONTRACTS and models_for_mode, props.PANORAMA_MODES, generation.refresh_panorama_models and _prepare_panorama, panels.draw_panorama_lane): Generate with Scenario Skybox Flux or GPT, From image with one still for HY World, HDRI with its outputs fixed to one OpenEXR file, and Upscale; panorama inputs that offer Saved panorama (downloaded LDR results of the selected scope whose saved metadata declares an equirectangular projection) and only Upload for a local file, which Upload reference checks as a 2:1 PNG or JPEG within 128 MiB and 32 megapixels before an upload bound to the checked bytes (panels.draw_references, panorama_lane, reference_form, panorama.inspect_panorama); results that stay saved because only Image-lane jobs apply automatically (model_jobs); and saved-job controls with the 360 label, Set panorama as World (N) and Make HDRI (N), which only selects the HDRI mode, model and saved reference without pricing or generating (saved_job_actions, panorama_lane.prefill_hdri). The HDRI input and the optional Flux restyle input take the same checked local 2:1 file as Upscale. Offline unit tests run on this checkout: test_panorama_contract, test_panorama, test_saved_job_actions, test_catalog_lanes and test_docs (330 passed). The Blender-native tests test_panorama_lane and test_composer were read, not run; earlier installed runs predate the current sources. An earlier physical pass on macOS arm64 Blender 5.1.2 at UI scales 1 and 2, on the exact packaged ZIP of the lane before its rebase onto #394 and with free quotes only, checked the tab, modes, mode-restricted model lists, settings and result lines, the upscale cap message and World application; the merged lane, the composer tab row, a local file through Upload reference and From image beyond its quote were not exercised physically, and no screenshot is committed. This review ran no paid or live generation and establishes no output format, size or asset layout, seam, pole or HDR range quality, other OS or DPI behaviour, or Blender 5.0 and 5.2 run. #98 closed on 2026-10-13 as delivered in 0.10.0; its remaining Environment checks (a desktop recheck of the merged lane with a local upload and From image, a paid HY World run, and seam, pole and HDR range review) continue in #440. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "5a627dd3a18d30092ce168797c91e1e971c4bd5f27d955f55fb91a10eb7e338d",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "184cbc93187f403e3241e80156d72ff9ef84f33056bb9f8a8d52b7ededaa7d66",
      "scenario/blender/generation.py": "5450f6b76f27108c6a3eafdbfcc5bd57b4c8ee070e17458b3e17be5aaa15bcd1",
      "scenario/blender/panorama_lane.py": "e18a0923ebfed1ab59c1795e547d58ca59e0ecb3f8f229d5c49c34312383067f",
      "scenario/blender/panels.py": "ed89c44a0d327f3a9de13d62f6bb44116e9ff88defdabc01e805900ee45c3d67",
      "scenario/blender/reference_form.py": "3b7433c9e3a9243f08a9fa031cf7bafddcdaa03ff5f2663455aa209f30ef5138",
      "scenario/core/ui/saved_job_actions.py": "637e7f0c4dc7892c9a953e160a4ef71aeb64fadd629bc054048623ac90f52306",
      "scenario/core/ui/composer_layout.py": "426c824ed377f9908988a7704909b4cd26b1d364ee9a22e645baacbf39ae9a7a",
      "scenario/blender/composer/state.py": "1686db41dc0b10dd6a8bdbd024b05da9e1c4651f9deac7bb967d5b5ee2814a29",
      "tests/blender/test_panorama_lane.py": "fe4a1b95e8c47881b78594df124c024557f27bcb1c1b1ad99851a6dab5441b22",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/unit/test_docs.py": "a8352a16f4caa43264cd87e1ea6cb616ab16c222bd760086f7594a6589184fb8",
      "scenario/blender/composer/modal.py": "45104e3c6c7081ef6b969551c2c04387524595f23ff8ce4bcbb70dea7e52957a",
      "tests/blender/test_composer.py": "abc3d487d8174e69ffad918081c4da697dd16aaf8c13cef70a64eff6b60a61d8",
      "scenario/blender/model_jobs.py": "956e032cbe134fc57a3f0aa2e996a1f06388b80f8f0561b16bd703763995240e",
      "scenario/core/scene/panorama.py": "3680feac102599bf04bf5b0e6a7a63f0d292c9536f9833848ba5217c8619a890",
      "tests/unit/test_panorama.py": "0b2006c19f9ce2edf276579d77745011664edaebfe4dc2d962b7b2dc1b03188a",
      "tests/unit/test_saved_job_actions.py": "dda2a3fe9bd4a6201beb32c2d7963ca91d7f6b001eb9cc1887552e10214adea6",
      "tests/unit/test_catalog_lanes.py": "a978ca89dd9198dd6bbf56b9b9f1d5c45fee7417f62c6ecbd13136225c1d2332"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/USER_GUIDE.md#environment).
