---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.uploads",
  "title": "docs/JOB_COORDINATOR.md: uploads",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "Scoped upload inspection, conservative recovery mapping, origin guards, complete upload configuration diagnostics and durable application tickets/claims/outcome receipts were inspected with the listed source/tests. Application verification covers offline ownership, races, lifecycle and persistence failures, not actual Blender mutation. Other API and runtime integration claims retain their prior evidence rather than a fresh claim-by-claim verification; no active UI/MCP adoption or live/paid operation acceptance is claimed.",
    "sources": {
      "scenario/core/jobs/upload_sources.py": "76a578fa9dda550391e8c1f31959983b4e7b64cf4bb9a2dafca834e1b99ca9ff",
      "scenario/core/jobs/upload_store.py": "e53e44059fba806e5284f75327277fc7dcfceb7cd8a5f77e7a57696ce6372cf8",
      "scenario/core/jobs/uploads.py": "73575da4b3f3589dead6a8b71d64feac2edcae789fb97f502b332fb5fe1789cc",
      "tests/blender/test_upload_commands.py": "496927b98c0774db28bac4da626f568bc147c9fc45f07da9e99a1aba0a0be9f1",
      "tests/unit/test_upload_commands.py": "5541ca299891a95ad0a41e4fe7261c74ba08a356261b68332517c20b7076fd76",
      "tests/unit/test_upload_inspection.py": "91a94ade8fbbb4f603273056b8db9b2bb8fbada3cbf910869b9e5b67a73044bd"
    },
    "scope": "uploads",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/JOB_COORDINATOR.md: uploads

Evidence for [the canonical document](../../JOB_COORDINATOR.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
