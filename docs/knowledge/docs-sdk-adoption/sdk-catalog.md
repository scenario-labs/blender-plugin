---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-catalog",
  "title": "docs/SDK_ADOPTION.md: sdk catalog",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "cfb68f28ec1c3ebe57ed9121998dce9eb2a20517e97cff0fc5ec652bb78a4b92",
      "tests/blender/test_offline_runtime.py": "0b6a0ba7517a44df951ba5a78af18896f0a5c981faefb1f95c73c1258804714c",
      "tests/unit/test_catalog_delivery.py": "12ec2fe0420c8363bca0fad22edf9b35a3ff8feb6bf2a13ed04c6befa7404586",
      "tests/unit/test_sdk_catalog.py": "91d56d6104d56e446a09e6a557bc6c15720c1590a0a5b55983994552e3fd8252"
    },
    "scope": "sdk-catalog",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/SDK_ADOPTION.md: sdk catalog

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
