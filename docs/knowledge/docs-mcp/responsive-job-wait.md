---
{
  "type": "Evidence",
  "id": "docs-mcp.responsive-job-wait",
  "title": "docs/MCP.md: responsive local job waits",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "responsive-job-wait",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Shared SDK waits retain deferred HTTP-thread observation and guarded main-thread completion; installed regression source covers delivery, changed credentials and stopped MCP without cancelling generation. Prototype waits now return an immediate read-only local snapshot instead of waiting on a retired engine. Their authenticated local read and timeout validation remain tested. Historical prototype waiter shutdown and record-replacement tests were retired with that engine. No live/paid service, desktop or complete release acceptance is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "1d613605107ee7db59790faec37e8a3bd4ee8a014c38b00e0b44be20b67f12c3",
      "scenario/mcp/protocol.py": "f41a0283918d116a77888b4d018d0d353ba80162be8c75f029a67ad774fcd976",
      "tests/blender/test_mcp_wait.py": "d6dd50e7b850e707bc8124665ecf415b84b51968c9ef02c4eb1fbffd4c2fad47",
      "tests/blender/test_mcp_contracts.py": "4c3bbbceed2a67cbeb81fba6a2f66dcfacb1f1d9bb5e9fe7ef0af88b582aa068",
      "tests/blender/run_all.py": "3caa22c1a3e84b870c8c6f0c6ba51e7e9f503e1db1512073fde4e17ff0d15cd8",
      "tests/blender/test_model_generation.py": "0ea4f5ef5c1211f922d453df93b0ef98d886c19c20faea2bf477ff6c2ce57b52"
    }
  }
}
---

Evidence for [the canonical document](../../MCP.md).
