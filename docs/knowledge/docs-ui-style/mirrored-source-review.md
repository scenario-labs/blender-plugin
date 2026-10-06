---
{
  "type": "Evidence",
  "id": "docs-ui-style.mirrored-source-review",
  "title": "Mirrored source coordinate review",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "mirrored-source-review",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "82f0abb2e8fe4cdeab78558c17491e250459bc77",
    "limits": "Reviewed native initial coordinate selection for mirrored/zero-scale sources, read-only explanatory UI, unchanged explicit MCP WORLD rejection, and the shared option validation. Tests cover negative, zero and positive determinants, unsupported option rejection/recovery, cancellation and preserved source transforms. The exact ZIP (SHA256 21edce46cf2c0e94095ba27668c2acef3b6b68968dc0dc0082921f1bd0760000) passes 670 native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Isolated Blender 5.1.2 desktop interaction exercised the mirrored-source dialog, Escape, coordinate choices, Return, viewport selection/front-view/zoom and separate completed-result reuse. The process exited cleanly with unchanged normal-profile fingerprints and no extra mocked service requests or submissions. Zero-scale behavior has headless native coverage only. No other OS desktop, provider alignment or release acceptance. Other topics retain their own evidence and source-drift warnings.",
    "sources": {
      "scenario/blender/job_recovery.py": "fe34f477610695ca8631184fa208d736ad49b360617c9cb1b2546ca1832bc926",
      "scenario/blender/model_jobs.py": "925f6000e83cb9aca1acf8f5c7822168e9c0f2b4eaf249803d851da7d3413fb5",
      "tests/blender/test_model_generation.py": "6fd3cec01b58164c0b66957fad69b237fa579ec0614d687ab9e641b6f3c0fba4",
      "docs/images/mirrored-mesh-before.png": "26550f045da820bb7a77f6857143356b21e83ba8e58c631ca1bd051b6898a45e",
      "docs/images/mirrored-mesh-approval.png": "6b1b1ff17210855949eb246835df377eef68238174c969518243c45ab570177b",
      "docs/images/mirrored-mesh-result.png": "4e2a09a04bce625f6735f1e278b5285f9b58d37fd7d3717069819e1600c406a7"
    }
  }
}
---

# Mirrored source coordinate review

Evidence for [the canonical guide](../../UI_STYLE.md).
