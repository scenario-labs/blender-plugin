---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.sdk-catalog",
  "title": "docs/architecture/runtime.md: sdk catalog",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged. Overlapping full-list refreshes now share one SDK pagination operation per privacy scope within the credential context. Offline contracts cover independent public/private reads, defensive copies, service failures, permission revocation, retirement and explicit retry while retaining the last complete cache. This does not establish live service or account/project identity acceptance.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "f63a55000afd55ddb8c737adc21e3f603cd4f517674639b6a2b15dae526d0c1e",
      "tests/blender/test_offline_runtime.py": "0b6a0ba7517a44df951ba5a78af18896f0a5c981faefb1f95c73c1258804714c",
      "tests/unit/test_catalog_delivery.py": "12ec2fe0420c8363bca0fad22edf9b35a3ff8feb6bf2a13ed04c6befa7404586",
      "tests/unit/test_sdk_catalog.py": "0881fe0cdc9778ee823254df329e6425507ec4b9bbcb6c7ec941c18f19b04c2f"
    },
    "scope": "sdk-catalog",
    "base_revision": "5d1f5a2062fed59b3a2fdefc621992467d34aea5"
  }
}
---

# docs/architecture/runtime.md: sdk catalog

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
