---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.complete-blockout-plans",
  "title": "Complete Blockout plan envelopes",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "complete-blockout-plans",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "2d073c8536174c7851dcea338ab9e92583129aa8",
    "limits": "Scoped parser and delivery regression review: complete JSON arrays may be wrapped in Markdown fences or prose; truncated prefixes, malformed arrays, non-array roots, non-object elements, non-finite values and oversized plans remain rejected. Synthetic delivery retains single approved submission and requires a separate geometry build. No live provider, desktop interaction, recovered-destination workflow or release acceptance is established.",
    "sources": {
      "scenario/core/scene/blockout.py": "6f46a011bfd5506ff7b6594074fb1684e708b86f5b467190e9e39e4223eac53a",
      "scenario/blender/blockout_jobs.py": "5cfd4e2c3b12573bba2e9308f02ac2bbaf71bea1e2e67913a3f0aecce71a6fa3",
      "tests/unit/test_blockout.py": "3b67bc39fd8cb18c1b9a720406c4fe31feff40ad10ac2688a658463ca4328d9f",
      "tests/blender/test_blockout_jobs.py": "b7abf455002ab9760b077659dbf4ccbec2334a725587bdc87278d14e81af8790"
    }
  }
}
---

# Complete Blockout plan envelopes

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#blockout-plan-commands).
