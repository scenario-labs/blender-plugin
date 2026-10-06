---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.mesh-approval-admission",
  "title": "Retired session guard at mesh approval admission",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "mesh-approval-admission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "82f0abb2e8fe4cdeab78558c17491e250459bc77",
    "limits": "Reviewed _apply_saved_mesh through validate_destination and _resolve: a retired session is rejected before verify_results. The direct facade native regression proves no verification call, queued command, durable record change, mesh/object mutation or extra mocked service requests. The consumed approval remains single-use, matching existing application paths. The guard already existed; this change adds regression evidence and documentation. Rebase integration also preserves cumulative static-model output references while handling MeshEditApplication receipt recovery separately. The exact ZIP (SHA256 64d86d96a625194b46f03055a9a3491993bfb83ab18560d895147e66e46a71fc) passes 668 installed native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with isolated profiles and unchanged normal-profile fingerprints. No fresh desktop interaction, live provider, other OS or release acceptance is claimed. Other topics retain their separate evidence and source-drift warnings.",
    "sources": {
      "scenario/blender/model_jobs.py": "925f6000e83cb9aca1acf8f5c7822168e9c0f2b4eaf249803d851da7d3413fb5",
      "scenario/blender/job_session.py": "5216d7c5b3dae533e653645526f40f2fa4d6d51b1534f5f12912546a042f0a49",
      "tests/blender/test_model_generation.py": "14a243b926c49a961725dad40458cd791f1773b991e56a27329e598e0cd8a18c"
    }
  }
}
---

# Retired session guard at mesh approval admission

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
