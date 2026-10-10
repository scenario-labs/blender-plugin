---
{
  "type": "Evidence",
  "id": "docs-mcp.upload-restart",
  "title": "recover_reference_upload restart action",
  "description": "MCP restarts an upload that cannot continue and returns a new reference handle.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "upload-restart",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the generated tool table, the restart action, its synchronous eligibility refusals and the returned reference_id/replacement_request_id. Installed native tests on macOS arm64 Blender 5.1.2 drive the MCP functions with live-shaped synthetic responses. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "ed4971751ef19827711d5bbe49b698b89a0d6b35f20627c94ae64b4d1d595592",
      "scenario/blender/reference_uploads.py": "baf59355688ad53ae084291e9860554fe305d71a7d1bb3ca01af66d73b5ef6cd",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/blender/test_reference_uploads.py": "7b3ddfa61ba562200e7258f53bd372d7782608e05cf977a466db1b86e28c109b",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd"
    }
  }
}
---

# recover_reference_upload restart action

Evidence for [the canonical document](../../MCP.md).
