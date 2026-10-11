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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the overview sentence, the generated tool rows, the hosted-parity rows and the Asset organization section against list_collections, prepare_asset_organization, apply_asset_organization and asset_organization_status, the initialize instructions and the AssetOrganization owner they call: argument validation before any request, the URL- and owner-free collection projection, context_id binding to the runtime job context, single-use apply, the apply description and guide wording that assets already in the collection are skipped and, when another client added some after the review, the rest are sent again within three add requests while nothing else is retried, request_count as the writes apply sends when each succeeds, status and discard without writes, phase notes (including the add_to_collection hint when prepare or apply finds the exact name taken, a discarded applied review keeping its result, and a discard after an unknown apply outcome warning that the change may already be in Scenario), the unknown-outcome report when the connection changes during apply, the apply description's return shape (FINISHED with a result object, or result null when the outcome is unknown, and NOT_SENT with result null and any collection holding the name in existing_collection_ids, matching review_payload and the not_sent and unknown paths of the shared owner), and recovery through status after an abandoned or timed-out apply. Hosted tool names were checked against the public hosted tool reference; the parity row's statement that the hosted collection_add_assets skips existing members and batches beyond 49 comes from the hosted Scenario MCP's behavior, not from a public reference. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service cover add, remove, tag, create-then-add, a member added between prepare and apply (two requests, VERIFIED), existing-name refusal at prepare and at apply, discard after apply and after an unknown apply outcome, request bodies and counts, mismatched or reused handles, credential and project switches, scene switch and file load, a session retired mid-apply, applied-then-lost writes with and without read-back, disabled online access, sanitized service errors, annotations and discovery; that service refuses a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave, and the latest installed run was on this branch after both restacks and the return-shape description fix, with 75 tools in installed discovery. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. The server's generic deferred-delivery timeout text is not organization-specific; the guidance routes it to status. No native Library control, desktop interaction, live MCP client run or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/MCP.md": "aa6e8905823be6ed18c456e2201c710fb6a929b2c929fe5ff84970a5b77e64aa",
      "scenario/mcp/tools_scenario.py": "6e4a3b38ae75521eea54daed93e2a8612dbf49b33eea8de968d084fd84260c99",
      "scenario/mcp/protocol.py": "8d8db78bf23a584436febafa9abd69cbd508235501222c21120f0f9d6339a59c",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/runtime.py": "318b14ef4b0c0ebac6cddeb498a58c571379e0f4a6e297d7b0752867a19bd0f3",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/test_mcp_contracts.py": "5ee268e3e181ac82505de33fbc5cd1e85d780e323445387d591c0c591282bf04",
      "tests/blender/run_all.py": "4e0e35175af8b2320b9dffb3910530b5ce5ff4f91eff9e8700ec15a4afa5e257",
      "tests/unit/test_mcp_descriptions.py": "6e17046814ea92bea18455b0e1d887e2320b9cd4f099311adfabafbd888fd030",
      "tests/unit/test_mcp_docs.py": "2728c6d5d71e7c7661278d8b5ccd5a0e374984d35d39868e81c2e5c6f3b2ab92"
    }
  }
}
---

# Local MCP asset organization tools

Evidence for [the canonical guide](../../MCP.md#asset-organization).
