---
{
  "type": "Evidence",
  "id": "docs-model-payload-audit.panorama-contract-models",
  "title": "Panorama contract models in the payload audit",
  "description": "The Environment lane's curated models join the default audit inventory.",
  "evidence": {
    "path": "docs/MODEL_PAYLOAD_AUDIT.md",
    "scope": "panorama-contract-models",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that DEFAULT_MODELS gains lane panorama, so surfaced_model_ids lists the five contract models with lane:panorama, and that an offline audit of their recorded fixtures reports five schemas, no fetch or schema failure and no finding at the LOW threshold, without credentials or an SDK client. This covers the audit heuristics only, not live schemas after 2026-10-10, generation or result handling.",
    "sources": {
      "docs/MODEL_PAYLOAD_AUDIT.md": "df651f909658b223c7777cd2f06be5215e225f3d98ab7fd84a5480475ca62e8e",
      "tools/audit_payloads.py": "bc72f41c8aaabaa2554dad87aea6c8bf9368b54a2d1626ec0e80622f6ba76063",
      "scenario/core/api/catalog.py": "4a10bc8754fbb00df0e6944da1fb9d068bb3944da110ca4bb87370c255a4e50d",
      "tests/unit/test_audit_payloads.py": "98670d78248e84aa07272e92c495751fb796124c45ba3873fbf456deaba4aa75",
      "tests/fixtures/models/model_scenario-skybox-flux.json": "767b3dec0bb22aaa70d95e56198420f9967cc8f7fd78f77aad813cec31ae11c7",
      "tests/fixtures/models/model_scenario-skybox-gpt.json": "f67b998b7c42f5d023ce86132d59e1c6caca7481e6c824ac48cf10590e66ca3a",
      "tests/fixtures/models/model_hunyuan-world-image-to-skybox.json": "3bc053b72792e54ebc8618ac72b22758314ae7828b053e9653c5590f0d28ba4c",
      "tests/fixtures/models/model_hdri-skybox.json": "c247920ad1119de9fa5cc7d9b0076285e9c1a8e63f33a55b7dee045eebfc4236",
      "tests/fixtures/models/model_sc-upscale-flux-skybox.json": "5dd2959d77200699842362fea7d78364b7d8c0f4be8a3c93ab6415cb295708cb"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/MODEL_PAYLOAD_AUDIT.md#what-it-checks).
