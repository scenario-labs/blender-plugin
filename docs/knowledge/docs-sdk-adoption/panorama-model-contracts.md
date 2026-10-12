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
    "limits": "Reviewed that the contracts use only the existing models.with_raw_response.retrieve and generate.with_raw_response.run_model paths through SDKAdapter.estimate_model and the coordinator, with dry_run only for quotes and max_retries=0 unchanged; no SDK method, extension or raw fallback is added and the adapter is unchanged. On 2026-10-10 the read-only recorder recorded the five model records with an API-key pair in its credential-bound scope and SDK 2.2.0; all are public custom records with status trained and no lineage. In the same scope 21 dryRun=true quotes through SDKAdapter.estimate_model covered every contract preset and all were accepted; none was submitted and ipDetection was not sent. Observed quote dependencies: Flux numOutputs, GPT quality, size and reference count, the HY World backend and the upscale factor change the quote, HDRI output toggles do not; an ordinary generated still was accepted as the image of the HDRI, upscale and Flux models, so an accepted quote does not show that a reference is a 360 panorama. The dry-run replies are summarized here and in the PR, not committed. Offline tests prepare every preset against the recorded schemas and the shared form preparation and pin the drift checks. Output formats, dimensions, asset counts, returned metadata.type and the HDR original host remain unverified until an authorized paid run.",
    "sources": {
      "docs/SDK_ADOPTION.md": "d7cab4dd1d6b8aa405e441784f3f2ad19a8d363d5075db651b4f4e382cc8e164",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "scenario/core/schema/forms.py": "6c13428b31421d71aa28f2f8fd2c95c7594eaa31fcadd49fc92782c462e274f6",
      "tools/record_fixtures.py": "031b32e0249041cce9b99d53f2fb02a2bf7663a3f220d800d26d23f19bb4998b",
      "tests/unit/test_panorama_contract.py": "88786e64bb96a7cddaba5d48164b097c8cfccf9128a7e22248662e2c1a533e0b",
      "tests/fixtures/models/model_scenario-skybox-flux.json": "767b3dec0bb22aaa70d95e56198420f9967cc8f7fd78f77aad813cec31ae11c7",
      "tests/fixtures/models/model_scenario-skybox-gpt.json": "f67b998b7c42f5d023ce86132d59e1c6caca7481e6c824ac48cf10590e66ca3a",
      "tests/fixtures/models/model_hunyuan-world-image-to-skybox.json": "3bc053b72792e54ebc8618ac72b22758314ae7828b053e9653c5590f0d28ba4c",
      "tests/fixtures/models/model_hdri-skybox.json": "c247920ad1119de9fa5cc7d9b0076285e9c1a8e63f33a55b7dee045eebfc4236",
      "tests/fixtures/models/model_sc-upscale-flux-skybox.json": "5dd2959d77200699842362fea7d78364b7d8c0f4be8a3c93ab6415cb295708cb"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/SDK_ADOPTION.md#panorama-model-contracts).
