---
{
  "type": "Evidence",
  "id": "docs-material-application.saved-material-eligibility",
  "title": "Saved material action eligibility",
  "evidence": {
    "path": "docs/MATERIAL_APPLICATION.md",
    "scope": "saved-material-eligibility",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "82f0abb2e8fe4cdeab78558c17491e250459bc77",
    "limits": "Reviewed the shared selected_maps metadata validator and its use by saved-job actions and material approval. Native regressions cover accepted PNG/EXR media types, rejected JPEG/WebP, missing receipts, repeated roles, and a supported albedo with an unsupported auxiliary map. An actual saved WebP-labelled result exposes no unusable material action and preparation queues no verification. Eligibility reads metadata only; the tests do not establish WebP decoding or replace subsequent byte and destination verification. The exact ZIP (SHA256 64d86d96a625194b46f03055a9a3491993bfb83ab18560d895147e66e46a71fc) passes 668 installed native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with isolated profiles and unchanged normal-profile fingerprints. No fresh desktop interaction, live provider, other OS or release acceptance is claimed. Other topics retain their separate evidence and source-drift warnings.",
    "sources": {
      "scenario/blender/model_jobs.py": "925f6000e83cb9aca1acf8f5c7822168e9c0f2b4eaf249803d851da7d3413fb5",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "tests/blender/test_model_generation.py": "14a243b926c49a961725dad40458cd791f1773b991e56a27329e598e0cd8a18c"
    }
  }
}
---

# Saved material action eligibility

Evidence for [the canonical guide](../../MATERIAL_APPLICATION.md).
