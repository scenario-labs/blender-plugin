---
{
  "type": "Evidence",
  "id": "docs-privacy.mcp-result-previews",
  "title": "Agent-requested preview reads",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that inspect_result_previews requests stills through the same scheduler, so Scenario stills read asset metadata and download preview images only while Online Access allows, for any downloaded saved job an agent names, while image stills and envelopes use local files only. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the roughness caption fix: the installed test file gained a roughness caption test, and for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed tools_scenario.py (three Film review and four asset organization tools, and other tools' workflow cost, Film composition, first-frame handoff, reference upload, inference-only cancellation, saved original, history row kind and cloud history changes); none of these changes touch inspect_result_previews, its specification or the scheduler wait it uses, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Re-checked on 2026-10-12 after the stack was replayed onto main at 4f169337, not a full re-review: main's saved mesh and splat imports and Film video export changed tools_scenario.py (Film export tools and the model import wording), job_session.py and test_mcp_descriptions.py, which makes 79 tools before this PR's inspect_result_previews and 80 with it in test_mcp_contracts.py; #419's review fixes changed result_previews.py to request a refused job's previews again after a delay and to keep its timer after a failed redraw. inspect_result_previews, its arguments, renditions, waits, retry and cancel, and the controller functions it calls (tile_targets, caption, forget_failures) are unchanged, so the claims above still hold. These sources' fingerprints are the current files'; the review date and base revision are unchanged. Also re-checked after the replay onto main at ff8d29d8, not a full re-review: main's Environment lane changed tools_scenario.py and test_mcp_descriptions.py for panorama contracts in list_models, estimate_cost and generate, and its compact composer job strip changed no MCP tool; MCP.md keeps main's Environment lane section before this PR's Saved result previews section, and the STUDIO_ADOPTION row keeps main's job strip sentence. inspect_result_previews is unchanged, so the claims above still hold; these fingerprints are the rebased files'.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "26c8c4d50f7791d30f696822c6e00e13381a5cb92b0f8cbba8df3186525dfd0a",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea"
    }
  }
}
---

# Agent-requested preview reads

Evidence for [the canonical guide](../../PRIVACY.md).
