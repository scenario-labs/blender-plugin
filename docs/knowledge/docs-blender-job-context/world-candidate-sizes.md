---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.world-candidate-sizes",
  "title": "World candidate size reads in the job session",
  "description": "How the session and model job owner queue and use World size reads.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "world-candidate-sizes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "0d266fa3c1397402686a841f8e979c0a1db9a0ca",
    "limits": "Reviewed on 2026-10-13: JobSession.world_sizes requires the main thread and an active connection, queues the coordinator's header read on the preview lane and returns its task, which is not added to the pending completions that drain returns. ModelJobs.poll records a finished read before projecting views, then queues at most one read of up to 128 downloaded World candidates of ready, apply_failed or applied jobs whose current receipt has no read size; a refused queue keeps them unread for a later poll and a failed read records them as unknown, which keeps the offer. Sizes stay in memory, keyed by request and asset and bound to the receipt digest, so a new download is read again. Installed tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 settle these reads through the shared delivery fixture and cover offered, refused and unknown sizes; see the World candidate evidence for the offer itself.",
    "sources": {
      "scenario/blender/job_session.py": "735db76ac83aa1c0e0a35532ed2a2fdd40cdbc67323f5f6e24f39ab2279720a6",
      "scenario/blender/model_jobs.py": "d563cf2640b33224915bd58404ab0c159abacfea44409b54529aa5cf272f2438",
      "tests/blender/test_model_generation.py": "1adba10cc19573a9043fbe3780a10e246cb7ed949c7655b673845e945c613d2e"
    }
  }
}
---

# World candidate size reads in the job session

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
