---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.job-storage",
  "title": "docs/SDK_UPLOADS.md: job storage",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "Windows upload source identity, public scoped inspection, conservative recovery mapping, optional core origin guards and JobSession forwarding were inspected with their listed offline and installed-native regressions. Other API and integration claims retain prior evidence rather than a fresh claim-by-claim verification. Active UI/MCP controls, production storage-host policy and authoritative account/project identity discovery remain separate; no live/paid operation acceptance is claimed.",
    "sources": {
      "scenario/core/jobs/store.py": "0053c3e48ce89ad699bab664f4f5fddc6af89f7cd01c8bbcab8a323c198c01fc",
      "tests/unit/test_job_store.py": "2bc71047d762d63d960ef249a30384ae41d508e5cf2f236e0e08c9caf6aba655"
    },
    "scope": "job-storage",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/SDK_UPLOADS.md: job storage

Evidence for [the canonical document](../../SDK_UPLOADS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
