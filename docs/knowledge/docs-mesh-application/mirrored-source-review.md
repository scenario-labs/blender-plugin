---
{
  "type": "Evidence",
  "id": "docs-mesh-application.mirrored-source-review",
  "title": "Mirrored source approval and local history",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "mirrored-source-review",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "82f0abb2e8fe4cdeab78558c17491e250459bc77",
    "limits": "Reviewed native initial coordinate selection for mirrored/zero-scale sources, read-only explanatory UI, unchanged explicit MCP WORLD rejection, and the shared option validation. Tests cover negative, zero and positive determinants, unsupported option rejection/recovery, cancellation and preserved source transforms. The exact ZIP (SHA256 21edce46cf2c0e94095ba27668c2acef3b6b68968dc0dc0082921f1bd0760000) passes 670 native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Isolated Blender 5.1.2 desktop interaction exercised the mirrored-source dialog, Escape, coordinate choices, Return, viewport selection/front-view/zoom and separate completed-result reuse. The process exited cleanly with unchanged normal-profile fingerprints and no extra mocked service requests or submissions. Zero-scale behavior has headless native coverage only. No other OS desktop, provider alignment or release acceptance. Reviewed the new mesh_edit local-application purpose through the session claim, storage allowlist, persisted decoding and status projection. Native and unit regressions distinguish model imports from mesh replacements after reopening storage and retain the original generation record and existing purpose labels. No schema field or version change, historical reclassification, live provider or global undo claim. Other topics retain their own evidence and source-drift warnings.",
    "sources": {
      "scenario/blender/job_recovery.py": "fe34f477610695ca8631184fa208d736ad49b360617c9cb1b2546ca1832bc926",
      "scenario/blender/model_jobs.py": "925f6000e83cb9aca1acf8f5c7822168e9c0f2b4eaf249803d851da7d3413fb5",
      "scenario/blender/job_session.py": "9aed31fe6298e1c80c33899e19dc8cd2735539706843c9e4c0b334d054837fcb",
      "scenario/core/jobs/store.py": "39148598ed88286b9933dcf4fe52e847d7ab073999a2c581c2f971e882a0911c",
      "tests/blender/test_model_generation.py": "6fd3cec01b58164c0b66957fad69b237fa579ec0614d687ab9e641b6f3c0fba4",
      "tests/unit/test_job_store.py": "5261ac660f822580f26c2ec6a29c31ee2dafad1e96d9032f60db2b0b3fe437dd"
    }
  }
}
---

# Mirrored source approval and local history

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
