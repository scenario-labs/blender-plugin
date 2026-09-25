---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.result-transfers",
  "title": "docs/JOB_COORDINATOR.md: result transfers",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "Scoped upload inspection, conservative recovery mapping, origin guards, complete upload configuration diagnostics and durable application tickets/claims/outcome receipts were inspected with the listed source/tests. Application verification covers offline ownership, races, lifecycle and persistence failures, not actual Blender mutation. Other API and runtime integration claims retain their prior evidence rather than a fresh claim-by-claim verification; no active UI/MCP adoption or live/paid operation acceptance is claimed.",
    "sources": {
      "scenario/core/jobs/results.py": "6f8735b1fe64f0607ae63c4a5cb43c443904730ede7a2466ceb6439a425d93a2",
      "tests/blender/test_result_commands.py": "bcb919c9a8dfcd3498959492b5bb49a3f1395b6923282f38182cc9b12c68089e",
      "tests/unit/test_result_commands.py": "3bcba6d1b719ad3016fd5a68e0b740ff5d7eaba1924d59700f0e6d6adbec8009"
    },
    "scope": "result-transfers",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/JOB_COORDINATOR.md: result transfers

Evidence for [the canonical document](../../JOB_COORDINATOR.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
