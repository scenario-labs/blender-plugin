---
{
  "type": "Evidence",
  "id": "docs-mcp.active-local-recovery",
  "title": "Active credential-scoped local job recovery",
  "description": "Application-owned session activation and local MCP inspection/cancellation.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "active-local-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "40c844be54ce827bc84d23fcd2d56505be941f7a",
    "limits": "Inspected runtime selection/retirement, independent SDK job-pool ownership with shared permission snapshot, local MCP inspection and revision/context-bound prepared cancellation. Offline/native tests cover reset, credential isolation, rejected stale-context cancellation, exact saved cost, failed session creation, and an in-flight synthetic receipt preserved in its old scope and reaped by the headless MCP loop. No paid entry-point migration, prototype record import, remote cancellation UI, transfer configuration, result application, live identity or paid acceptance is claimed.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "422921904da57f6c06b59399fa437b76972c517ef342fadd2cd459607745ff67",
      "scenario/blender/runtime.py": "50b74bdfce810f053f3e8dd5ad991b9cd583dd8f3d7b0f7c2980d15bf6b6325e",
      "scenario/blender/job_session.py": "2f6247e8f52959bbd87fe25e679a4055bef878a696934fafd44d654a923849f2",
      "scenario/blender/mcp_service.py": "276d497cded4082828b39c8672c16cc71b7b0fb748ac663d63cdbc1447d8c0c4",
      "scenario/mcp/tools_scenario.py": "369deabc88005682eee11d6a729ca92b41a28c30261f351b88e600e9fe9c1fec",
      "tests/unit/test_sdk_catalog.py": "c56c958d5b4a15e34283cda08c817c6833d98c6fa0868af2a7f758e67cbf7e54",
      "tests/unit/test_mcp_descriptions.py": "f2529d4c84ba564f119611bbfbac15b3070289255840e4f54e3b8d317142625c",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tests/blender/test_runtime_jobs.py": "e5964322f9405d373fa2ee4fe2ac9c1775359d745496fc093089eb19a90b85cf",
      "tests/blender/test_mcp_contracts.py": "cf979d470a2d3eda533009d2081fbcb021a63e24c4a64e5c3b78441e9e2b6a9a"
    }
  }
}
---

# Active credential-scoped local job recovery

Evidence for [the canonical document](../../MCP.md).
