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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Inspected the Environment lane contract cases in tools/smoke_image.py and tools/smoke_suite.py: panorama_case requires the hdri kind for model_hdri-skybox and the panorama kind for the other four contract models before any request, accepts only exact {\"$panorama\": RUN} placeholders in contract inputs that take a saved 360 panorama and refuses them anywhere else; quote reads the model with SDKAdapter.model and applies panorama_contract.prepare plus the schema validation before the dry run, storing version 4 quote records with the prepared parameters and verified references; submit reapplies the contract to the fresh schema after the attempt marker (exit 3 on drift or a changed body) and older records of contract models cannot submit (exit 4). resolve_panoramas and saved_results open a completed run's store with the selected key pair and project, require the saved quote scope, one finished job and receipt-verified files through an offline adapter, and take the first is_ldr_panorama result whose bytes pass inspect_panorama as a PNG or JPEG container, recording its measured size; OpenEXR bytes are refused whatever media type the asset declares. The suite checks every case and resolves every placeholder before its directory, quotes or version-2 uploads; --saved-runs exists only for quote and budget-run. The hosted workflow invocation was read, not run. Offline tests in tests/unit/test_smoke_panorama.py use the real SDK adapter, coordinator, stores and suite with recorded skybox schemas and synthetic PNG, JPEG and OpenEXR headers, including both documented plans checked against the recorded schemas and an OpenEXR file saved as an image/png 360 result, refused with no request and no quote record; single mutations of each check were caught. A zero-spend live quote of a Flux and a GPT text case in the test scope produced version 4 records with the contract bodies. No paid run, upload, live skybox output, HDRI conversion or hosted dispatch is claimed; #98 acceptance remains open. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): the hosted workflow now chooses the committed monthly plan or the private plan secret (#390), so a hosted first suite runs as a private plan; the World candidate rule added to panorama.py (#394) does not change inspect_panorama, which these cases use.",
    "sources": {
      "tools/smoke_image.py": "61e540d79ae9dc743f287199f152707ca183808084e3bc14c6786c07122318f3",
      "tools/smoke_suite.py": "1b88c666cd76840a8d24a2056c5314096b738ba497c530cb449618c76b895c4e",
      "tools/smoke_inputs.py": "ae7b7cc04bcc60658159ecad4a6a312d8742206ec1aaaf8bc61d511ad4ffc0c2",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/core/scene/panorama.py": "3680feac102599bf04bf5b0e6a7a63f0d292c9536f9833848ba5217c8619a890",
      ".github/workflows/smoke.yml": "aeec8197a964fbce4f9dbe52096e857c62e714a7825af8c0c1ded38ea40fb6fe",
      "tests/unit/test_smoke_panorama.py": "e47f1ed2e594da734b0303ecebee867d0b935198c005a87a9db6643dea7ae42d"
    }
  }
}
---

# Panorama contract cases in model checks and suites

Evidence for [the canonical guide](../../../tests/smoke/README.md#panorama-contract-cases).
