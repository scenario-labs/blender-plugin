---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.cloud-metadata-delivery",
  "title": "Cloud metadata delivery across Blender context changes",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "cloud-metadata-delivery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "9891339fd2dc86cd54cb49820e76c8a4044ea750",
    "limits": "Cloud metadata remains bound to its active coordinator/session and exact issued job/model/scope, with single-use delivery; scene changes before or during a read preserve original provenance without application authority. Native recovery permits Edit/Sculpt/Pose modes with existing network/credential gates. Expected admission reasons remain actionable; unexpected errors remain generic. Final ZIP 38f0a51edea77643f4988c737090e759b578c4b1844cdfd25f4ec43c3f3183d6 passes 822 installed tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. Offline desktop input on that ZIP in 5.1.2 proves Edit Mode admission, scene switching and hidden-panel completion, repeat inspection, viewport selection and Home framing with one mocked GET, zero downloads/submissions, profile cleanup and unchanged normal profile. Tests cover retired owners, copied/foreign/non-cloud completions, changed/deleted origins and unchanged guarded general delivery. This does not establish live provider, other OS desktop or release acceptance. Earlier screenshots retain their named artifact limits.",
    "sources": {
      "scenario/blender/operators.py": "af2b33d82fdde21c3bb83b787d8ca15c3f96950f43c99aa06db7b3d884fd39d8",
      "scenario/blender/model_jobs.py": "6c3a67c25999db6cb5d878c163831fa412a0132705bcf240943528444410e989",
      "scenario/blender/job_session.py": "3b1daa63c01e9efbd7c3ba08593f5addd0f6372b343d1ac1c2ea1269fffba352",
      "scenario/core/jobs/coordinator.py": "78cbcdc1bbe529c2b3fc0db243b915c6b9cd7afdfcb782c20e9c0ff0ee057762",
      "scenario/mcp/tools_scenario.py": "1f0cf79f3205c4f6972a87c8704d5f0faecfccb177fbf6edbbdb1c61681dca0d",
      "tests/blender/test_model_generation.py": "f6a40f11ca4a5b84b35f428730e7a241369542b2182eb6e3d06522f63d4373de",
      "tests/blender/test_job_session.py": "745c14eb7cf075f22ef059da1d02c3611f4c08653267cd8fb96b882ed8e937be",
      "tests/unit/test_cloud_job_recovery.py": "6663d26d37a13fba59d3c9e74579e84be0b39a264f4a2f4ee2d243b138da1499",
      "docs/images/cloud-recovery-edit-mode.png": "1638a4fe8305923bdb05fec27bf539c03ebb31bafba26adc5226be44a53a8ea5",
      "docs/images/cloud-recovery-scene-switch.png": "32bbf27eedc318118539b99ee786901ba859a931251334fa25a521263c62678e"
    }
  }
}
---

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
