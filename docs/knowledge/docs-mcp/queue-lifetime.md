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
    "reviewed_at": "2026-09-26",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Source and concurrent offline regression tests cover queued expiry, late pump delivery, stopped admission, waiter release, completed-result races and uncertainty after execution starts. HTTP native regression covers timed-out mutation rejection and stop/restart without replay. This does not establish remote cancellation, durable paid submission safety or complete product acceptance. Exact installed-ZIP suites pass all 342 tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64; other platforms and human acceptance are separate. Review follow-up covers SystemExit, KeyboardInterrupt and GeneratorExit: the waiting caller receives a tool error promptly while the main-thread interruption still propagates.",
    "sources": {
      "scenario/mcp/server.py": "f4d26b38c6fade34b10c8e7cad7a3ea208b526de01958cb9682cfd1ad7848d85",
      "scenario/mcp/protocol.py": "62b2fbfa2f3e4bcb6f8084f3b67798d97fe11c01a4ba38b062ddf52c8c68413b",
      "tests/unit/test_mcp_queue.py": "c8e06ae5f8e4c95c986f90a132991e0ef332fed7b5fb3718ce6da0b0bba3a72d",
      "tests/blender/test_mcp_server.py": "5bb65580cd98dd04eb100df698f887b8fe1d244c6a0ea630e6b9b52622a5ba32"
    }
  }
}
---

# MCP queue lifetime

Evidence for [the canonical document](../../MCP.md).
