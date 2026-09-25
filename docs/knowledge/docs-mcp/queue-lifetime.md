---
{
  "type": "Evidence",
  "id": "docs-mcp.queue-lifetime",
  "title": "MCP queue lifetime",
  "description": "Local request admission, timeout and shutdown execution boundaries.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "queue-lifetime",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Source and concurrent offline regression tests cover queued expiry, late pump delivery, stopped admission, waiter release, completed-result races and uncertainty after execution starts. HTTP native regression covers timed-out mutation rejection and stop/restart without replay. This does not establish remote cancellation, durable paid submission safety or complete product acceptance. Exact installed-ZIP suites pass all 342 tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64; other platforms and human acceptance are separate.",
    "sources": {
      "scenario/mcp/server.py": "b1c9a790459d3d3bdbb8e19c81d45eab6fe4e4f90a82cb6a413caef8e058f594",
      "scenario/mcp/protocol.py": "62b2fbfa2f3e4bcb6f8084f3b67798d97fe11c01a4ba38b062ddf52c8c68413b",
      "tests/unit/test_mcp_queue.py": "87ede761f13ba0bff34ea58ced1566282ea01daf2109e893954c207bada08040",
      "tests/blender/test_mcp_server.py": "5bb65580cd98dd04eb100df698f887b8fe1d244c6a0ea630e6b9b52622a5ba32"
    }
  }
}
---

# MCP queue lifetime

Evidence for [the canonical document](../../MCP.md).
