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
    "limits": "Inspected shared SDK quote, lane-bound single-use approval, durable submission, download/recovery and saved-result inspection for all MCP model lanes. Native fixtures exercise exact costs, changed lane/input/context rejection, uncertainty, restart, cancellation and no implicit non-image application. This is not live provider acceptance, non-image UI integration, reference/media application parity or release approval. Non-image results remain ready; original lane metadata is not persisted. Cold prototype status, wait and import resolve persisted local registry IDs before shared credential access; native regressions exercise both local and remote IDs without a shared session or service client.",
    "sources": {
      "scenario/blender/model_jobs.py": "505277706caf7b036024b57db64bd5ca96e783c3ee53a1e6ead9f44cc030ca21",
      "scenario/mcp/tools_scenario.py": "1635b46976211df460bad9c2f92a7a97fdc2872f1b9e60e36e284bae7fe36c1c",
      "scenario/blender/generation.py": "add487ba125ff012dcd0f73acaa1640d91f1a8be4eda71008c7c9c36e3972832",
      "tests/blender/test_model_generation.py": "529d9f43abcee923c387be4f30a4284bf62e6418476cffb63fb45b726417056d",
      "tests/unit/test_mcp_descriptions.py": "104a3278279beb2ee40e761da71d23410c721998f707e8c822572f9ee46001bf",
      "tests/blender/test_mcp_contracts.py": "333f26a522c26592ccc3bd210a79c5e984a63c0c914cc64b53a910e568e1f87f"
    }
  }
}
---

# MCP model-lane quotes and durable submission

Evidence for [the canonical guide](../../MCP.md).
