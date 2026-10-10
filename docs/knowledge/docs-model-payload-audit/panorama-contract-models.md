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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that DEFAULT_MODELS gains lane panorama, so surfaced_model_ids lists the five contract models with lane:panorama, and that an offline audit of their recorded fixtures reports five schemas, no fetch or schema failure and no finding at the LOW threshold, without credentials or an SDK client. This covers the audit heuristics only, not live schemas after 2026-10-10, generation or result handling.",
    "sources": {
      "docs/MODEL_PAYLOAD_AUDIT.md": "69675dac91c1ba0477fed62262476e5a35b334d76df7f8029ac94fd0297e0ccf",
      "tools/audit_payloads.py": "518a4d1972faf72298f3dadc5d8656e2b17be67fb31ed3fd93263ff62ffef257",
      "scenario/core/api/catalog.py": "474e4996d5bd2eda8109b452157d2179664814db0f6d6ac297d385aca974d1b1",
      "tests/unit/test_audit_payloads.py": "2615d8d0bb3ba2bef3c081017f1e218c49aea0eb0f2bf982581c1ec79c1e448a",
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
