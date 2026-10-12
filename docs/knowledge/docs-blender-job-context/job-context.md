---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.job-context",
  "title": "docs/BLENDER_JOB_CONTEXT.md: job context",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "coverage": "inherited",
    "reviewed_at": "2026-10-12",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. On 2026-10-12 re-reviewed only the Origin and quote lifetime section's session-side capture and invalidation claims against job_session.py, origins.py, test_job_session.py and test_job_origins.py, adding the JobSession.synchronizing exception: inside the block, main-thread dependency and frame updates to a named scene revoke none of that scene's origins, and because OriginRevisions keeps one revision per scene this includes origins other features captured there; other scenes, updates outside the block, pruning of deleted scenes and targets, render-thread resets, Undo/Redo and file loading still invalidate. Installed session tests cover the synchronizing scope and dependency, frame, render-thread, deleted scene and target and file-load invalidation; Undo/Redo was checked in source only. The coordinator-side registry guard and upload claim statements were not rechecked. The job_session.py, test_job_session.py and test_job_origins.py fingerprints record this origin review only: the World application, lifecycle, component, format and restoration claims were not rechecked against them, and test_application_claims.py keeps its earlier fingerprint.",
    "sources": {
      "scenario/blender/job_session.py": "67fe502720edc1100f7b9af721408f6e9a29cb1b5525ffac027f8028bd28a5b5",
      "scenario/core/jobs/origins.py": "d1282d67aacdfe2444a776cf1338667bea9ee67392ff3f473db581a0f8059977",
      "tests/blender/test_job_session.py": "0636dd715e5f6e20cf729c975f3a47d9d432a802daf7c1fa47f779a7790e78dd",
      "tests/unit/test_application_claims.py": "e2b993b16b8b97a9705ad68b46c2823c3c8006a32a73bd9968143605cb369989",
      "tests/unit/test_job_origins.py": "fd2bb50bd0a8f2a204878a69e3003d43ec5fb56867ce24ad1da662623244e576"
    },
    "scope": "job-context",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b"
  }
}
---

# docs/BLENDER_JOB_CONTEXT.md: job context

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
