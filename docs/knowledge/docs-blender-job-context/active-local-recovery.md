---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.active-local-recovery",
  "title": "Active credential-scoped local job recovery",
  "description": "Application-owned session activation and local MCP inspection/cancellation.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "active-local-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "40c844be54ce827bc84d23fcd2d56505be941f7a",
    "limits": "Inspected runtime selection/retirement, independent SDK job-pool ownership with shared permission snapshot, local MCP inspection and revision/context-bound prepared cancellation. Offline/native tests cover reset, real blend-file save/load with token invalidation, credential isolation, rejected stale-context cancellation, exact saved cost, failed session creation, and an in-flight synthetic receipt preserved in its old scope and reaped by the actual headless CLI loop. No paid entry-point migration, prototype record import, remote cancellation UI, transfer configuration, result application, live identity or paid acceptance is claimed.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "422921904da57f6c06b59399fa437b76972c517ef342fadd2cd459607745ff67",
      "scenario/blender/runtime.py": "131048374f1edaa4aafc863bee8ceb3e4ea3a9fe9b9bec733f5d0c2f5b9d18b7",
      "scenario/blender/job_session.py": "f64c6acb518d4bb26c453f1aa0d07c788355334b5da85506512e9a20b13de655",
      "scenario/blender/mcp_service.py": "f56b2020dadeef23ae089a5a649bbbb99fa4cba407994ebd8f3d12c1680495b9",
      "scenario/mcp/tools_scenario.py": "369deabc88005682eee11d6a729ca92b41a28c30261f351b88e600e9fe9c1fec",
      "tests/unit/test_sdk_catalog.py": "c56c958d5b4a15e34283cda08c817c6833d98c6fa0868af2a7f758e67cbf7e54",
      "tests/unit/test_mcp_descriptions.py": "f2529d4c84ba564f119611bbfbac15b3070289255840e4f54e3b8d317142625c",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tests/blender/test_runtime_jobs.py": "41fedce234988a672a42c0ee88058d0d29be89cb55a5d4874beab25772484525",
      "tests/blender/test_mcp_contracts.py": "cf979d470a2d3eda533009d2081fbcb021a63e24c4a64e5c3b78441e9e2b6a9a",
      "scenario/mcp/server.py": "2268544089dbab0e37a8ee64544942afb1b0970eab8f32201b13e7d9995e6db1",
      "tests/unit/test_mcp_server.py": "6631822e89fcdaa0d696f5a34fe899de177f0baafe837b4447a55477691b31c4"
    }
  }
}
---

# Active credential-scoped local job recovery

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
