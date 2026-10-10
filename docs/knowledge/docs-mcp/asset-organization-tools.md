---
{
  "type": "Evidence",
  "id": "docs-mcp.asset-organization-tools",
  "title": "Local MCP collection and tag organization tools",
  "description": "list_collections and the prepare, apply and status tools over the session-owned organization reviews.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "asset-organization-tools",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the overview sentence, the generated tool rows, the hosted-parity rows and the Asset organization section against list_collections, prepare_asset_organization, apply_asset_organization and asset_organization_status, the initialize instructions and the AssetOrganization owner they call: argument validation before any request, the URL- and owner-free collection projection, context_id binding to the runtime job context, single-use apply, the apply description and guide wording that assets already in the collection are skipped and, when another client added some after the review, the rest are sent again within three add requests while nothing else is retried, request_count as the writes apply sends when each succeeds, status and discard without writes, phase notes (including the add_to_collection hint when prepare or apply finds the exact name taken, a discarded applied review keeping its result, and a discard after an unknown apply outcome warning that the change may already be in Scenario), the unknown-outcome report when the connection changes during apply, and recovery through status after an abandoned or timed-out apply. Hosted tool names were checked against the public hosted tool reference; the parity row's statement that the hosted collection_add_assets skips existing members and batches beyond 49 comes from the hosted Scenario MCP's behavior, not from a public reference. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service cover add, remove, tag, create-then-add, a member added between prepare and apply (two requests, VERIFIED), existing-name refusal at prepare and at apply, discard after apply and after an unknown apply outcome, request bodies and counts, mismatched or reused handles, credential and project switches, scene switch and file load, a session retired mid-apply, applied-then-lost writes with and without read-back, disabled online access, sanitized service errors, annotations and discovery; that service refuses a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave, and the latest installed run was on the stacked Library head that contains this branch. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. The server's generic deferred-delivery timeout text is not organization-specific; the guidance routes it to status. No native Library control, desktop interaction, live MCP client run or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/MCP.md": "6b532b51b8ed9e5bb54a58220193b3a6d7f45fd0322b439e50785269cb067fda",
      "scenario/mcp/tools_scenario.py": "f4e87186806f93466220ef04f7c2530f0532ded790d4a8754a2a5b81183db08a",
      "scenario/mcp/protocol.py": "a33b66bdc80e18dbee8d283bf6c2e4a507025a0be93f39773a1b138c7fba8ce7",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/runtime.py": "9468693ddd2941575470018633b425885401ae68551c89fc88773ef0fce20933",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/test_mcp_contracts.py": "cfc081b7b2d8550f778643b9a275082e92e35e11cacb56c90fae054ce605388d",
      "tests/blender/run_all.py": "b3019328085a8334dd3347248a9b145d3a23533ffbafcfac9304962df189a6c8",
      "tests/unit/test_mcp_descriptions.py": "54f0dd69090d9c5b7f3c64cee686afa6c5b80b057831acb8b2e5e85326fcebfb",
      "tests/unit/test_mcp_docs.py": "2728c6d5d71e7c7661278d8b5ccd5a0e374984d35d39868e81c2e5c6f3b2ab92"
    }
  }
}
---

# Local MCP asset organization tools

Evidence for [the canonical guide](../../MCP.md#asset-organization).
