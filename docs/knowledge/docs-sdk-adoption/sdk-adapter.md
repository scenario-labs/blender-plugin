---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-adapter",
  "title": "docs/SDK_ADOPTION.md: sdk adapter",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-10-13",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed. Single-page model reads and development fixture recorder mapping reviewed against the pinned SDK 2.1.0 artifact and offline request/failure contracts. No live fixture recording or media-rights acceptance is claimed. Exact packaged Blender 5.0.1 macOS arm64 baseline passed, including the new single-page SDK contract; broader hosted platform checks are separate. Estimate parsing re-reviewed on 2026-10-13: a dry-run response that carries a job raises EstimateStartedJob and issues no Estimate; synthetic transports only.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "c08a94f319c08d8427a3a3f7aeceb690915d964a99cafbbc25d5f004c2781b93",
      "tests/unit/test_scenario_sdk_contract.py": "69c3e06092104358ac2b48529feacc794a756bbe697705aeff02d6984e593362",
      "tests/unit/test_sdk_adapter.py": "e496061f89d60da284ae056478c85c254b2cffc77992904e1b86a344a381b01b"
    },
    "scope": "sdk-adapter",
    "base_revision": "3221af5a67583d5a992e9f25f9c41d00abed8924"
  }
}
---

# docs/SDK_ADOPTION.md: sdk adapter

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
