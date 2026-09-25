---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-bundle",
  "title": "docs/SDK_ADOPTION.md: sdk bundle",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed. Single-page model reads and development fixture recorder mapping reviewed against the pinned SDK 2.1.0 artifact and offline request/failure contracts. No live fixture recording or media-rights acceptance is claimed. Exact packaged Blender 5.0.1 macOS arm64 baseline passed, including the new single-page SDK contract; broader hosted platform checks are separate.",
    "sources": {
      "tests/blender/test_sdk_bundle.py": "0b1b83f6b8cb728ab8c341982d24375129dbaf26a0b2ac4112d1613bab73db72"
    },
    "scope": "sdk-bundle",
    "base_revision": "e013a26d7208f472b0d5d6fee1534763e2632f22"
  }
}
---

# docs/SDK_ADOPTION.md: sdk bundle

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
