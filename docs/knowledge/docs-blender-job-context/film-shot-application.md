---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.film-shot-application",
  "title": "Shared Film shot verification and application",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "film-shot-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Shared shot source selection, owned receipt verification, explicit single-use destination review, all-source claims before mutation, native rollback and owner-local receipt-only recovery. Synthetic offline/native tests cover saved scope, transitive task digests, stale records, shared sources, restart, deleted/changed scenes, transient delivery context, partial claims and failed acknowledgements. This command adds no native/MCP control registration, timeline approval, SDK request, download, store or worker pool. Desktop interaction, live provider compatibility, capture/finishing/export and release acceptance remain unproved. Explicit inspected dismissal preserves durable uncertainty and pending receipt authority; regression coverage includes cache capacity and pre-write failure recovery. Finished verification drains while another scene is current. Saturated admission preserves completed hero verification and retries the unqueued read after origin/recipe/source checks; no scene work or paid submission is replayed. Native tests cover session capacity, worker admission and changed recipes while waiting.",
    "sources": {
      "scenario/core/jobs/film_sources.py": "fa79cc34f3611eeb93a41a378d3585cfdf03c84014d008098c56a1c2d2d4ac18",
      "scenario/core/jobs/film_tasks.py": "dea0522e39f9272d951275a00a04a16b69af9b2b05bb77afb70c0962ffaea1a6",
      "scenario/blender/film_application.py": "8de2dc5a80ee97a9c175076638d4ec8db8aac3bc579325292cc8b08f55a5d4ed",
      "scenario/blender/film_scene.py": "b4193e062049de8287d830e6e6e5ea74e5a15ef1e88d213255c74b0f951ecaa8",
      "scenario/blender/job_session.py": "ef36c50910218e21db563a9f70b64b8717dd51a552e8d3560ff6fd3d7514e366",
      "scenario/core/jobs/coordinator.py": "3dcf192150b0a661303ae04244d5ea8c37d30c7096ad068cd7ff6af038ecdad6",
      "tests/unit/test_film_sources.py": "523ebd4d96625cf0564e838bead59bb638abfce2e97cab30df252539abd112d4",
      "tests/blender/test_film_application.py": "02a8549c3d7b70338000ebf06c66207727047f7c2e503cc3bf94b4a964cbf13b"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
