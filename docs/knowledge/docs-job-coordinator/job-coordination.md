---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.job-coordination",
  "title": "docs/JOB_COORDINATOR.md: job coordination",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "Scoped upload inspection, conservative recovery mapping, origin guards, complete upload configuration diagnostics and durable application tickets/claims/outcome receipts were inspected with the listed source/tests. Application verification covers offline ownership, races, lifecycle and persistence failures, not actual Blender mutation. Other API and runtime integration claims retain their prior evidence rather than a fresh claim-by-claim verification; no active UI/MCP adoption or live/paid operation acceptance is claimed.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "c4c8e9d40cce9da0d858883ac198c40b801859202f453e56eb53441b468d7ac2",
      "scenario/core/jobs/workers.py": "fc584737c05c28bcb20309220ed6dc99bb40b330339b995075c1392497d3ebed",
      "tests/unit/test_job_cancellation.py": "0d26f5fdd7896e86c9730cf64a9dad3a23ac58caf7f04f365809cbdedd186732",
      "tests/unit/test_job_coordinator.py": "ac8d3ac91dfee6df7fa00029d05324588bcff807cf34eaa48acaa82449fee5e0",
      "tests/unit/test_shared_quotes.py": "2f824c1999c1d9ed83e1c23960bfedaf09ed921c73f87252a68389976f290133"
    },
    "scope": "job-coordination",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/JOB_COORDINATOR.md: job coordination

Evidence for [the canonical document](../../JOB_COORDINATOR.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
