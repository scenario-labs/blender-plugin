---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.mcp-result-previews",
  "title": "Local MCP use of the preview scheduler",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the MCP tool's checks (context token, saved revision, previewable state), its requests, retry with the controller's forget_failures and cancel, and the watch that pump sets, deactivate releases through the scheduler's close, and the final main-thread read in an unchanged context and session. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the roughness caption fix: caption() now reads ROLE_LABEL from core.jobs.result_previews, which labels every role in result_metadata.TEXTURE_ROLES, so inspect_result_previews reports a roughness map as Roughness (N), the same caption as its tile. A new installed test checks that caption and fails on the previous head without the fix; for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/blender/result_previews.py": "8c9a836b6322c2ecd24506d68b46186b8addf3a2de3acec12569df07e6ab44d9",
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea"
    }
  }
}
---

# Local MCP use of the preview scheduler

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
