---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-adapter",
  "title": "docs/SDK_ADOPTION.md: sdk adapter",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "a18daa427bd16d7b9bfbf0ed322fe4d7c3bdca27f161db8766f28042ec8e5a0b",
      "tests/unit/test_scenario_sdk_contract.py": "69c3e06092104358ac2b48529feacc794a756bbe697705aeff02d6984e593362",
      "tests/unit/test_sdk_adapter.py": "94af37a52b3fb048b95cfe4fd73f9d2d8a307dd84167a63a50c266fe6a212ae1"
    },
    "scope": "sdk-adapter",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/SDK_ADOPTION.md: sdk adapter

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
