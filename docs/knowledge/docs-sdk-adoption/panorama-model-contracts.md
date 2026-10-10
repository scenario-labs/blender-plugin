---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.panorama-model-contracts",
  "title": "Panorama model contracts",
  "description": "SDK methods and zero-spend evidence behind the panorama contracts.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "panorama-model-contracts",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that the contracts use only the existing models.with_raw_response.retrieve and generate.with_raw_response.run_model paths through SDKAdapter.estimate_model and the coordinator, with dry_run only for quotes and max_retries=0 unchanged; no SDK method, extension or raw fallback is added and the adapter is unchanged. The native Environment form reaches the same path through ModelJobs.quote and submit, and the helpers added for it (saved_panorama_refs, is_ldr_panorama, reference_rule, result_line, mode descriptions and size presets) make no service call. On 2026-10-10 the read-only recorder recorded the five model records with an API-key pair in its credential-bound scope and SDK 2.2.0; all are public custom records with status trained and no lineage. In the same scope 21 dryRun=true quotes through SDKAdapter.estimate_model covered every contract preset and all were accepted; none was submitted and ipDetection was not sent. Observed quote dependencies: Flux numOutputs, GPT quality, size and reference count, the HY World backend and the upscale factor change the quote, HDRI output toggles do not; an ordinary generated still was accepted as the image of the HDRI, upscale and Flux models, so an accepted quote does not show that a reference is a 360 panorama. The dry-run replies are summarized here and in the PR, not committed. Offline tests prepare every preset against the recorded schemas and the shared form preparation and pin the drift checks. Output formats, dimensions, asset counts, returned metadata.type and the HDR original host remain unverified until an authorized paid run.",
    "sources": {
      "docs/SDK_ADOPTION.md": "83d174c1094545303e7b221474857bc4fe1f51757264ae3f57b85d7e75a001ec",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/core/schema/forms.py": "bc1e91677c33f2a0f9ff0a8ce7be51ba238653aab52d9d88e3e37fd23ab962b4",
      "tools/record_fixtures.py": "11943f62e9ec02c1962c35e47a368f6de3acff705ec2d48fbb2a2ea69f99e340",
      "tests/unit/test_panorama_contract.py": "03b45364309d8d1f2c5016966ed794f8f215088e6ed42047b0fdaf62cf53be70",
      "tests/fixtures/models/model_scenario-skybox-flux.json": "767b3dec0bb22aaa70d95e56198420f9967cc8f7fd78f77aad813cec31ae11c7",
      "tests/fixtures/models/model_scenario-skybox-gpt.json": "f67b998b7c42f5d023ce86132d59e1c6caca7481e6c824ac48cf10590e66ca3a",
      "tests/fixtures/models/model_hunyuan-world-image-to-skybox.json": "3bc053b72792e54ebc8618ac72b22758314ae7828b053e9653c5590f0d28ba4c",
      "tests/fixtures/models/model_hdri-skybox.json": "c247920ad1119de9fa5cc7d9b0076285e9c1a8e63f33a55b7dee045eebfc4236",
      "tests/fixtures/models/model_sc-upscale-flux-skybox.json": "5dd2959d77200699842362fea7d78364b7d8c0f4be8a3c93ab6415cb295708cb",
      "scenario/blender/generation.py": "265c53ce191b2b8d9f0eabecc1f0a726aa5758b0fae958ff1cae9b9aa0d620dd",
      "scenario/blender/model_jobs.py": "b5174cdf8a73fea86b633fb660a7d942b0fd0f2516e81ec7477e1be6bb956b6b"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/SDK_ADOPTION.md#panorama-model-contracts).
