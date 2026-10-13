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
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed on 2026-10-13: JobSession.world_sizes requires the main thread and an active connection, queues the coordinator's header read on the preview lane and returns its task, which is not added to the pending completions that drain returns. ModelJobs.poll records a finished read before projecting views, then queues at most one read of up to one preview batch of downloaded World candidates of ready, apply_failed or applied jobs whose current receipt has no read size; a refused queue keeps them unread for a later poll and a failed read records them as unknown, which keeps the offer. Sizes stay in memory, keyed by request and asset and bound to the receipt digest, so a new download is read again. Installed tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 settle these reads through the shared delivery fixture and cover offered, refused and unknown sizes; see the World candidate evidence for the offer itself. Review follow-up on 2026-10-13: the 512-entry eviction is removed, because it reread evicted candidates every poll once more than 512 were shown. Each poll that walks the views now forgets the sizes of jobs no longer in them, so a shown job keeps its size and is not read again, and each read takes at most the preview scheduler's BATCH_LIMIT (32) candidates, enforced by ResultCommands.world_sizes too, with the next poll reading the rest. Native tests cover the pruning and the batched follow-up reads, and a unit test a full batch; fingerprints of the files this follow-up edits were refreshed.",
    "sources": {
      "scenario/blender/job_session.py": "735db76ac83aa1c0e0a35532ed2a2fdd40cdbc67323f5f6e24f39ab2279720a6",
      "scenario/blender/model_jobs.py": "4c8e5c07cc81a0dbe681388a209cade4cddd3ca81b949c94e8fdc9b9463a1089",
      "tests/blender/test_model_generation.py": "b4b8560032649218aa9077f3c0cdc976e3226866d3ca01804eace8e0a158bb85"
    }
  }
}
---

# World candidate size reads in the job session

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
