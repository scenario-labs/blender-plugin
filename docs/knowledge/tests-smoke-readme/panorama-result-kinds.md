---
{
  "type": "Evidence",
  "id": "tests-smoke-readme.panorama-result-kinds",
  "title": "Panorama and HDRI model check result kinds",
  "description": "Projection, saved original and 2:1 container checks for panorama and hdri runs.",
  "evidence": {
    "path": "tests/smoke/README.md",
    "scope": "panorama-result-kinds",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Inspected the panorama and hdri result kinds in tools/smoke_image.py: every saved result must be an image, only results whose saved projection is equirectangular are inspected, each such verified file must pass the bounded 2:1 PNG, JPEG or OpenEXR panorama preflight (inspect_panorama) shared with World application, and hdri additionally needs a source: original result labelled image/x-exr or image/aces whose container is OpenEXR. The suite plan accepts both kinds through RESULT_KINDS. Offline tests use the real SDK adapter, coordinator, store and result commands with mocked service responses and synthetic PNG, JPEG and OpenEXR headers: accepted projections with image companions, an accepted 2:1 JPEG panorama, missing or skybox-3d projections, square files, malformed JPEG bytes, a video companion, preview-only, Radiance, PNG and JPEG originals, plus a seven-kind aggregate suite. No live skybox output, pixel decoding, dynamic range, seam review or paid run is claimed; #98 acceptance remains open. Environment lane contract models must use these kinds (hdri for model_hdri-skybox, panorama for the other four); tests/unit/test_smoke_panorama.py exercises both kinds through the contract path. Re-checked 2026-10-12 after restacking on main 4bd0061d: main's later changes to these sources (untransformed original downloads #391, previews, splats, waveforms, the first-frame handoff, binary smoke records #382 and the World candidate rule #394) leave the panorama and hdri kind checks unchanged. Re-checked 2026-10-12 after contract_body began passing schema.exclusive to validate: the claims above are unchanged by that one-line change and its offline test.",
    "sources": {
      "tools/smoke_image.py": "3fc1b8decae54b0e0553d5501843bc4ce64936566e6da98f39e2970b1425f461",
      "tools/smoke_suite.py": "1b88c666cd76840a8d24a2056c5314096b738ba497c530cb449618c76b895c4e",
      "scenario/core/scene/panorama.py": "3680feac102599bf04bf5b0e6a7a63f0d292c9536f9833848ba5217c8619a890",
      "scenario/core/jobs/result_metadata.py": "c16b9788e7836ea2ab77a8675506bea1409989da935de801f16c30ee626f5cb1",
      "scenario/core/jobs/results.py": "fbf05ea8baed20b055b946a1eef66337b698002c1b8066de1551b84adfb2f4b7",
      "tests/unit/test_smoke_image.py": "6ca35975d98fc9b82e7a27f9b918d7f5da67ffdb6a4a7a1e3a3a012d3ecabff1",
      "tests/unit/test_smoke_suite.py": "ee39b9c1b324ccf001a7491affea19f4194d30c2f81e0ba5e41a8cc62c51cd29",
      "tests/unit/test_panorama.py": "0b2006c19f9ce2edf276579d77745011664edaebfe4dc2d962b7b2dc1b03188a",
      "tests/unit/test_smoke_panorama.py": "01ec629e80e0dfdfcd049f211721b5dc7f6d0527df4180271e645fb44224fcfd"
    }
  }
}
---

# Panorama and HDRI model check result kinds

Evidence for [the canonical guide](../../../tests/smoke/README.md#result-kinds-and-entry-points).
