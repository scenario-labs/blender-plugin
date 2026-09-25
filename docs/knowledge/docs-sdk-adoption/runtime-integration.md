---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.runtime-integration",
  "title": "docs/SDK_ADOPTION.md: runtime integration",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed.",
    "sources": {
      "tests/blender/test_generation.py": "5c95b7409d2b20c0a8ce10498ad613dcf8fbd2bd9ab613b541e04754060ee866"
    },
    "scope": "runtime-integration",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/SDK_ADOPTION.md: runtime integration

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
