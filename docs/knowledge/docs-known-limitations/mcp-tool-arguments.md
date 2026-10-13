---
{
  "type": "Evidence",
  "id": "docs-known-limitations.mcp-tool-arguments",
  "title": "Local MCP tools receive unchecked arguments",
  "description": "The local MCP server passes tool arguments to handlers without checking the schema's required fields.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "mcp-tool-arguments",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "4dfca796e1a082d89e0a0af091e78e161fa77fca",
    "limits": "Reviewed on main 4dfca796 that protocol.handle_message passes params['arguments'] straight to the tool handler without checking the input schema's required list; that reference_upload_status declares context_id and reference_id required, that _upload_context answers a missing or different context_id with 'The upload context changed; list saved uploads again', and that a missing reference_id raises KeyError from args['reference_id'], which tool_failure_text reports as 'failed unexpectedly; see the Blender console' because the extension did not write that message. Other tools' handling of omitted arguments was not enumerated. A maintainer-authorized end-to-end run through local MCP met the context_id case (private report).",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "50d988107d579b172936cd16b8d601e5d99fc46cb1e3929aabf685c9c0e2893a",
      "scenario/mcp/protocol.py": "7686624495c114548474ef7d388d0795ded70e5e45efc7c0f3271bd540790514",
      "scenario/mcp/tools_scenario.py": "112da784a70a39e76b052acc966f7378c924cb86ec3246a9fe0625685088d0f7"
    }
  }
}
---

# Local MCP tools receive unchecked arguments

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#runtime-and-authentication).
