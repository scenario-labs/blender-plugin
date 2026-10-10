---
{
  "type": "Evidence",
  "id": "docs-mcp.tool-failure-text",
  "title": "docs/MCP.md: tool failure text",
  "description": "What a failed local MCP tool call returns to the client and what stays in the local log.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "tool-failure-text",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the failure paragraph in the security model and the failed-unexpectedly troubleshooting entry against protocol.py, sandbox.py, the server's interrupted-handler path, the scenario logger configuration and the Log Level preference. Offline tests cover messages raised by extension code (validation ValueError, refusing PermissionError, still-loading and interrupted RuntimeError, a wrapped OSError), extension error classes raised from outside, C-call failures inside extension frames (open, int, dict lookup, bare and named re-raise, a PermissionError naming a file), errors raised outside the extension, the executor and deferred finish paths, and sandbox tracebacks for runtime, syntax, blocked sys.exit, chained, exception group and deep recursion errors, on Python 3.11 and 3.13. Sandbox tests compare the bounded traceback extraction with a full walk and count the frames it extracts; the leading-frame bound assumes the sandbox module's frames only open (run_python) or end (the sys.exit guard) a traceback. The extension-origin rule reads the innermost frame's module and opcode; it was checked on CPython 3.11 and 3.13 only. An installed Blender 5.1.2 test covers kept messages and sanitized conversion and file-read failures through the real tool registry. Messages of the extension's own error classes and raise statements are trusted: an audit of raise statements with dynamic text found path-bearing text only in UI-only code (3D file import, model picker thumbnails), which MCP tools do not call. execute_python still returns frames of code the agent called, such as Blender's modules. No MCP client application, GUI session, Windows or Linux run, or Blender 5.0 or 5.2 run is claimed here.",
    "sources": {
      "scenario/mcp/protocol.py": "693ab2f6fc736e5f4e584b39eb3835eb410d8ae07d6b2ef3e5b012440e5482ca",
      "scenario/mcp/sandbox.py": "16ba8427232244b18cc947a7f99760520c3af1772fd2762a4e87b190f5aaf1ef",
      "scenario/mcp/server.py": "2268544089dbab0e37a8ee64544942afb1b0970eab8f32201b13e7d9995e6db1",
      "scenario/blender/registry.py": "0d024ec188c190acda096aa68387ce3270c60a3bc4a47344603f1bb775c0c31c",
      "scenario/prefs.py": "569ef8524cb0ba9e7d8f5b46582d4903b05d96a7cbc6cf1f2b3216be23c4ba96",
      "tests/unit/test_mcp_protocol.py": "248322d99aae4f4bbc11ab832e54dbe7689dee80e3f332f8e321d7b2d6838c4c",
      "tests/unit/test_mcp_sandbox.py": "469dab3a2c8e64a457624ea92399109472ab378891dcdca625b8d738e99d5ee6",
      "tests/unit/test_mcp_queue.py": "c8e06ae5f8e4c95c986f90a132991e0ef332fed7b5fb3718ce6da0b0bba3a72d",
      "tests/blender/test_mcp_security.py": "327fef3a0e51d40fd35ffd486468413d6e77955c260f10ed94beb50a6f76e65c"
    }
  }
}
---

# docs/MCP.md: tool failure text

Evidence for [the canonical document](../../MCP.md).
