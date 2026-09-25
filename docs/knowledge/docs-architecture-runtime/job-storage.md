---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.job-storage",
  "title": "docs/architecture/runtime.md: job storage",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged.",
    "sources": {
      "scenario/core/jobs/store.py": "0053c3e48ce89ad699bab664f4f5fddc6af89f7cd01c8bbcab8a323c198c01fc",
      "tests/blender/test_job_store.py": "9391c63dd8837345ea383e2a2fa250d9a911c1a3ddda16e07617c66854b2fc65"
    },
    "scope": "job-storage",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/architecture/runtime.md: job storage

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
