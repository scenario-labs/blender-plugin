---
{
  "type": "Evidence",
  "id": "docs-mcp.film-task-recovery",
  "title": "Recover interrupted Film preparation through inspection",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "film-task-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "88a6e2c296aba52f938501dbdabf259aef555127",
    "limits": "Recipe inspection drains already-admitted preparation in the unchanged original scene, exposes the existing exact quote for approval or discard, and reports pending preparation or saved upload associations. It starts no new network work and does not resume saved jobs. Native regressions cover cross-scene quote isolation, recovered discard and one-time approval, stale-origin refusal, interrupted upload inspection and idempotent retry. A conflicting upload request or observed revision is rejected before admission, preserving bound status even after presentation-action eviction. This is offline source/native evidence, not physical desktop input or live provider acceptance.",
    "sources": {
      "scenario/blender/film_jobs.py": "6d7bd3f2ffa0d0ce573cd6cb223d4e699090412349308075645e9715783153ed",
      "scenario/mcp/tools_scenario.py": "b7fcf0b8eb2010fba727f5328c6223be6fcc6975d00c59f1b25850bfc6408bc0",
      "tests/blender/test_film_controls.py": "c362c57f5d25a7336b2dcb17e94ecbeaf8f6b51432d43f92896a70a250f397db"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
