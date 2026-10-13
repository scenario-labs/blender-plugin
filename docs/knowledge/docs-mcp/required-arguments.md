---
{
  "type": "Evidence",
  "id": "docs-mcp.required-arguments",
  "title": "docs/MCP.md: required tool arguments",
  "description": "A call that omits a required argument is refused before its tool runs.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "required-arguments",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "4dfca796e1a082d89e0a0af091e78e161fa77fca",
    "limits": "Reviewed that handle_message refuses a tools/call before the executor or handler runs when its arguments are a nonempty value that is not an object, or omit a name in the tool's inputSchema required list, returning a ValueError isError result through the existing failure-text rule; absent or empty arguments still mean an empty object. Only presence is checked, not types or values, which each tool still validates. A static audit of the registered tools found 68 with required arguments (134 fields): handlers read 83 of them by subscript, so a missing one failed as an unexpected KeyError, and several compared a missing context_id with the current context and reported a changed context, as reference_upload_status did. job_status, wait_for_job and import_result declare no required argument because they accept job_id or id. Unit tests cover the singular and plural refusals, a non-object, that neither the executor nor the handler runs, and that a complete call reaches the handler. An installed test calls reference_upload_status through the real registry without context_id and without reference_id; it failed on main with the changed-context and KeyError texts. The full installed suite passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 (2003 tests each, 3 skipped). No MCP client application was exercised.",
    "sources": {
      "scenario/mcp/protocol.py": "093caacbfa65b12b8cdbdc73cd0db292bc4efa31cdb9983775088cf93bd101d4",
      "scenario/mcp/tools_scenario.py": "f9e4447cc3b1a1cae05f5fd3148940f25f39c3bbfbbc62b876ab524b5af0d83f",
      "scenario/mcp/tools_blender.py": "13bf44bdb3721b13e689ea88c91ad4031444a7ce08bec4bbff01958e23691037",
      "scenario/blender/mcp_service.py": "f56b2020dadeef23ae089a5a649bbbb99fa4cba407994ebd8f3d12c1680495b9",
      "tests/unit/test_mcp_protocol.py": "0bb31bcae3d8138f3d55441145cda774d0cb9df832c202a2db44f194100384f8",
      "tests/blender/test_reference_uploads.py": "567e65da79edb8878fa09163962e1363ffe754ada8a070ba0e12d8858fdf735b",
      "tests/blender/helpers.py": "283317572fdd825a7d9068ea72b876799a1485dc9502d6d2763518e503a0d61d"
    }
  }
}
---

# Required tool arguments

Evidence for [the canonical document](../../MCP.md).
