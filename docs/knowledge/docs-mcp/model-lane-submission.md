---
{
  "type": "Evidence",
  "id": "docs-mcp.model-lane-submission",
  "title": "MCP model-lane quotes and durable submission",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "model-lane-submission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "29abc71f35c858af941328e02282aaaa865e595a",
    "limits": "Inspected shared SDK quote, lane-bound single-use approval, durable submission, download/recovery and saved-result inspection for all MCP model lanes. Native fixtures exercise exact costs, changed lane/input/context rejection, uncertainty, restart, cancellation and no implicit non-image application. This is not live provider acceptance, non-image UI integration, reference/media application parity or release approval. Non-image results remain ready; original lane metadata is not persisted. Cold prototype status, wait and import resolve persisted local registry IDs before shared credential access; native regressions exercise both local and remote IDs without a shared session or service client. Completed prototype lookups leave the manager uninitialized and the registry unchanged even when an unrelated remote job is pending and online access is enabled; active prototype lookups retain manager-owned records.",
    "sources": {
      "scenario/blender/model_jobs.py": "505277706caf7b036024b57db64bd5ca96e783c3ee53a1e6ead9f44cc030ca21",
      "scenario/mcp/tools_scenario.py": "0e24a4ac41ccddbe410d35ff36d38d009519be663fea08ad90e83ee4502c2621",
      "scenario/blender/generation.py": "add487ba125ff012dcd0f73acaa1640d91f1a8be4eda71008c7c9c36e3972832",
      "tests/blender/test_model_generation.py": "529d9f43abcee923c387be4f30a4284bf62e6418476cffb63fb45b726417056d",
      "tests/unit/test_mcp_descriptions.py": "104a3278279beb2ee40e761da71d23410c721998f707e8c822572f9ee46001bf",
      "tests/blender/test_mcp_contracts.py": "f070cef34fc404c4b03d8be2421c156ac7a6b4761c3a2ec4ef870a7da9fbd526"
    }
  }
}
---

# MCP model-lane quotes and durable submission

Evidence for [the canonical guide](../../MCP.md).
