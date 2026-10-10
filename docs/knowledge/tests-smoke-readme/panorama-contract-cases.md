---
{
  "type": "Evidence",
  "id": "tests-smoke-readme.panorama-contract-cases",
  "title": "Panorama contract cases in model checks and suites",
  "description": "Contract preparation, saved panorama placeholders and the two-suite panorama plans.",
  "evidence": {
    "path": "tests/smoke/README.md",
    "scope": "panorama-contract-cases",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the Environment lane contract cases in tools/smoke_image.py and tools/smoke_suite.py: panorama_case requires the hdri kind for model_hdri-skybox and the panorama kind for the other four contract models before any request, accepts only exact {\"$panorama\": RUN} placeholders in contract inputs that take a saved 360 panorama and refuses them anywhere else; quote reads the model with SDKAdapter.model and applies panorama_contract.prepare plus the schema validation before the dry run, storing version 4 quote records with the prepared parameters and verified references; submit reapplies the contract to the fresh schema after the attempt marker (exit 3 on drift or a changed body) and older records of contract models cannot submit (exit 4). resolve_panoramas and saved_results open a completed run's store with the selected key pair and project, require the saved quote scope, one finished job and receipt-verified files through an offline adapter, and take the first is_ldr_panorama result whose bytes pass inspect_panorama, recording its measured size. The suite checks every case and resolves every placeholder before its directory, quotes or version-2 uploads; --saved-runs exists only for quote and budget-run. The hosted workflow invocation was read, not run. Offline tests in tests/unit/test_smoke_panorama.py use the real SDK adapter, coordinator, stores and suite with recorded skybox schemas and synthetic PNG, JPEG and OpenEXR headers, including both documented plans checked against the recorded schemas; single mutations of each check were caught. A zero-spend live quote of a Flux and a GPT text case in the test scope produced version 4 records with the contract bodies. No paid run, upload, live skybox output, HDRI conversion or hosted dispatch is claimed; #98 acceptance remains open.",
    "sources": {
      "tools/smoke_image.py": "9e9da23fcfb42eca4d379004d1b55a6bc6d57c25080d1fdd1a3d1b3ed39ff32a",
      "tools/smoke_suite.py": "1b88c666cd76840a8d24a2056c5314096b738ba497c530cb449618c76b895c4e",
      "tools/smoke_inputs.py": "3386ad525e8d9d9f4214dea1b6d05ec78084dfd02e00abf6305d904d2ef04526",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      ".github/workflows/smoke.yml": "71ea95047895ceefb2ac8220663b2f6ee5a4b2dcf56dd4a8b5c8f3cee9a7b9bb",
      "tests/unit/test_smoke_panorama.py": "f82108630c3bde6db2f170ff82952a3d33ccd16b0bc05eac1e8566c0f0be75ef"
    }
  }
}
---

# Panorama contract cases in model checks and suites

Evidence for [the canonical guide](../../../tests/smoke/README.md#panorama-contract-cases).
