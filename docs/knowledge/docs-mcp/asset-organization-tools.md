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
    "limits": "Reviewed the overview sentence, the generated tool rows, the hosted-parity rows and the Asset organization section against list_collections, prepare_asset_organization, apply_asset_organization and asset_organization_status, the initialize instructions and the AssetOrganization owner they call: argument validation before any request, the URL- and owner-free collection projection, context_id binding to the runtime job context, single-use apply, status and discard without writes, phase notes, the unknown-outcome report when the connection changes during apply, and recovery through status after an abandoned or timed-out apply. Hosted tool names were checked against the public hosted tool reference. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service cover add, remove, tag, create-then-add, existing-name refusal, request bodies and counts, mismatched or reused handles, credential and project switches, scene switch and file load, a session retired mid-apply, applied-then-lost writes with and without read-back, disabled online access, sanitized service errors, annotations and discovery. No live collection, tag or bulk request was made; service name uniqueness, re-adding a member, DELETE body survival, tag normalization and live limits remain unverified. The server's generic deferred-delivery timeout text is not organization-specific; the guidance routes it to status. No native Library control, desktop interaction, live MCP client run or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/MCP.md": "aefb5848e0845b05e2410c71e8c5d1a5b9fd86c003ba03db09226a40e9eb4b7f",
      "scenario/mcp/tools_scenario.py": "aaf9b83134f6367f096b1205c5cb4cfffdbd53ba6a33d2630f1d32650d92d593",
      "scenario/mcp/protocol.py": "a33b66bdc80e18dbee8d283bf6c2e4a507025a0be93f39773a1b138c7fba8ce7",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/core/jobs/organization.py": "7f69ce28e4c54e3c2b819cc76735d001671de6bcfcb12145b2cd90b059e8b84d",
      "scenario/blender/runtime.py": "4dd15c99e830769b970cbffb8a2d895c657bc52be66b6e4c1e01a8ebebd5ed00",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/blender/test_asset_organization.py": "3d4e5c2d92b5c07941e546ddd9bcbb985c54f0296aba86e7de32fc1a73132fca",
      "tests/blender/test_mcp_contracts.py": "cfc081b7b2d8550f778643b9a275082e92e35e11cacb56c90fae054ce605388d",
      "tests/blender/run_all.py": "aaf1d5affa3c7e35555a318e610d6c8f13d97878a8eccf65f91a58a30c8a603e",
      "tests/unit/test_mcp_descriptions.py": "0be21d36c99cc8a2570fe49041cc1bb061a82d2fc03c95202e985038e00d44b6",
      "tests/unit/test_mcp_docs.py": "2728c6d5d71e7c7661278d8b5ccd5a0e374984d35d39868e81c2e5c6f3b2ab92"
    }
  }
}
---

# Local MCP asset organization tools

Evidence for [the canonical guide](../../MCP.md#asset-organization).
