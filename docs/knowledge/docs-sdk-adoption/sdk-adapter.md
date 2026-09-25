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
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed. Single-page model reads and development fixture recorder mapping reviewed against the pinned SDK 2.1.0 artifact and offline request/failure contracts. No live fixture recording or media-rights acceptance is claimed. Exact packaged Blender 5.0.1 macOS arm64 baseline passed, including the new single-page SDK contract; broader hosted platform checks are separate.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "c6e89405e668a38a0d68237c9cab183cfcb8ef289fc8396595979dbf44c71b80",
      "tests/unit/test_scenario_sdk_contract.py": "69c3e06092104358ac2b48529feacc794a756bbe697705aeff02d6984e593362",
      "tests/unit/test_sdk_adapter.py": "0adceb2f6b7566ee6203ed4779d3373bb39df3971673f5853e40d5fc56497fd0"
    },
    "scope": "sdk-adapter",
    "base_revision": "e013a26d7208f472b0d5d6fee1534763e2632f22"
  }
}
---

# docs/SDK_ADOPTION.md: sdk adapter

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
