---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.job-context",
  "title": "docs/JOB_COORDINATOR.md: job context",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "Scoped upload inspection, conservative recovery mapping, origin guards, complete upload configuration diagnostics and durable application tickets/claims/outcome receipts were inspected with the listed source/tests. Application verification covers offline ownership, races, lifecycle and persistence failures, not actual Blender mutation. Other API and runtime integration claims retain their prior evidence rather than a fresh claim-by-claim verification; no active UI/MCP adoption or live/paid operation acceptance is claimed.",
    "sources": {
      "scenario/core/jobs/origins.py": "d1282d67aacdfe2444a776cf1338667bea9ee67392ff3f473db581a0f8059977",
      "tests/unit/test_application_claims.py": "e2b993b16b8b97a9705ad68b46c2823c3c8006a32a73bd9968143605cb369989",
      "tests/unit/test_job_origins.py": "06cc03625e3504999732c7526dca1c0b1732da62aa967c4e1a30071b3b3b9e0b"
    },
    "scope": "job-context",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/JOB_COORDINATOR.md: job context

Evidence for [the canonical document](../../JOB_COORDINATOR.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
