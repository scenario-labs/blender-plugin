---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.job-context",
  "title": "docs/SDK_UPLOADS.md: job context",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "Windows upload source identity, public scoped inspection, conservative recovery mapping, optional core origin guards and JobSession forwarding were inspected with their listed offline and installed-native regressions. Other API and integration claims retain prior evidence rather than a fresh claim-by-claim verification. Active UI/MCP controls, production storage-host policy and authoritative account/project identity discovery remain separate; no live/paid operation acceptance is claimed.",
    "sources": {
      "scenario/blender/job_session.py": "73f0a3e2e892c5535331f1c1a2b812d2e70a77e70f27cd6a33c079317d52ea83",
      "scenario/core/jobs/origins.py": "d1282d67aacdfe2444a776cf1338667bea9ee67392ff3f473db581a0f8059977",
      "tests/unit/test_job_origins.py": "06cc03625e3504999732c7526dca1c0b1732da62aa967c4e1a30071b3b3b9e0b"
    },
    "scope": "job-context",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/SDK_UPLOADS.md: job context

Evidence for [the canonical document](../../SDK_UPLOADS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
