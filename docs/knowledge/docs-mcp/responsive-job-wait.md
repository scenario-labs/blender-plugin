---
{
  "type": "Evidence",
  "id": "docs-mcp.responsive-job-wait",
  "title": "docs/MCP.md: responsive local job waits",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "responsive-job-wait",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Reviewed bounded HTTP-thread observation of a captured local record with main-thread preparation and guarded completion. Native tests cover authenticated concurrent scene access, terminal outcomes, invalid timeout bounds, shutdown and stale credentials/manager/record rejection on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. This does not prove live or paid generation, scoped durable job adoption, completed scene application, other platforms or general cancellation. It reuses the deferred protocol from the merged estimates change.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "dca93caefb24a940bff3c99d2440ecf91659c4fe0777e42adbb71ee9350ea7aa",
      "scenario/mcp/protocol.py": "f41a0283918d116a77888b4d018d0d353ba80162be8c75f029a67ad774fcd976",
      "tests/blender/test_mcp_wait.py": "93ac761525543c095319bcf1770bf190ab0fa23579dc12e7d63794eaa41b6cf3",
      "tests/blender/test_mcp_contracts.py": "14db7e13774c4b3c94182c42ae33676ff37b87e4e869fe5e382a82349e2b04f0",
      "tests/blender/run_all.py": "93ecb30bfa06dffb1ff1fc1190930ece24a75ae702d9e01d8d40a15d7b28040b"
    }
  }
}
---

Evidence for [the canonical document](../../MCP.md).
