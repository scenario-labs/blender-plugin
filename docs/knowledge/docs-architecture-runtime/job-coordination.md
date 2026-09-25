---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.job-coordination",
  "title": "docs/architecture/runtime.md: job coordination",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "c4c8e9d40cce9da0d858883ac198c40b801859202f453e56eb53441b468d7ac2",
      "scenario/core/jobs/manager.py": "00e9d6c9bc9971a63afca06a45761acf0a676cec7ade783bd215a64c4ff103b4",
      "scenario/core/jobs/workers.py": "fc584737c05c28bcb20309220ed6dc99bb40b330339b995075c1392497d3ebed",
      "tests/unit/test_shared_quotes.py": "2f824c1999c1d9ed83e1c23960bfedaf09ed921c73f87252a68389976f290133"
    },
    "scope": "job-coordination",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/architecture/runtime.md: job coordination

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
