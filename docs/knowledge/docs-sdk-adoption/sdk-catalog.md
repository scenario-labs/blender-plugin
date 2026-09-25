---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-catalog",
  "title": "docs/SDK_ADOPTION.md: sdk catalog",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-25",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed. Overlapping full-list refreshes now share one SDK pagination operation per privacy scope within the credential context. Offline contracts cover independent public/private reads, defensive copies, service failures, permission revocation, retirement and explicit retry while retaining the last complete cache. This does not establish live service or account/project identity acceptance. Malformed list-record conversion now completes before cache publication and maps AttributeError, TypeError and ValueError to a sanitized ScenarioError. Regression tests reproduce bad capabilities and tags on later pages with overlapping public/private callers, preserve the prior complete list, verify catalog_failed delivery rather than generic worker errors, and permit explicit retry. This scoped fix does not change model-detail normalization, API methods, credentials, SDK dependencies or live acceptance.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "b3c1e5c418fc9beba2cb3fa222621ffb0474ac0ddbaca650402a22cde1430345",
      "tests/blender/test_offline_runtime.py": "0b6a0ba7517a44df951ba5a78af18896f0a5c981faefb1f95c73c1258804714c",
      "tests/unit/test_catalog_delivery.py": "68964dab7ec3b0d35dae1d0e33cc7911b2e8d385639a653d513935fd64ba1891",
      "tests/unit/test_sdk_catalog.py": "943b512fd1555e4515231558333ffe68bf6c4bb7d00a2761b13a1bab68e7354c"
    },
    "scope": "sdk-catalog",
    "base_revision": "1ee01d1a8a1568c333290d7476f3a2d9bc066240"
  }
}
---

# docs/SDK_ADOPTION.md: sdk catalog

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
