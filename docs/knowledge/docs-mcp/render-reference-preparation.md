---
{
  "type": "Evidence",
  "id": "docs-mcp.render-reference-preparation",
  "title": "Explicit render reference preparation",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "render-reference-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "65c48337d19c4f93127ad8c5e6f21f5e045f808c",
    "limits": "Inspected explicit native render scene/first-frame slots using the existing typed SDK upload lifecycle and exact quote/submission boundary. Six added native tests cover prepared render submission once, quote invalidation, guarded scene upload, preadmission cleanup, optional first-frame upload/exclusion and late role edits. The exact ZIP SHA256 604200f8efdd2a8b96ad364e067b26d62fb9495794d4707cb0db02859bea7a10 passes 552 offline native tests each on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. A 5.0.1 desktop probe demonstrated capture/upload control, native text edits, refreshed quote, one mock submission and viewport selection/navigation. It subsequently crashed with a background SQLite job-read traceback; root cause and clean desktop completion remain unresolved. Captures and transport were synthetic, no paid/live call occurred, and other OS/CPU, real encoding, Render Video desktop interaction and release acceptance are not established. Automatic Prompt Spark, non-image result application and Film remain separate work. MCP callers still supply final model parameters directly; this adds no API endpoint, SDK fallback or dependency pin.",
    "sources": {
      "scenario/blender/render_references.py": "ca13ca03952d4bdfe13c8280e46f192fb5e7e525778393cdba2c9d71ae37db71",
      "scenario/blender/generation.py": "c442d732b2f44156237368dee90d3dddbf5e5dd44e5cb7b19c9e201e91d4dd23",
      "scenario/blender/reference_form.py": "9652fb1aa2644be3fb81bb59ba4d8034f0ea979ae50462701f607daf8d4b420d",
      "scenario/blender/render_lanes.py": "2da15f2b6f405d256d5646179ebaeb365045811a89d0f2e96fdc9d40cbe099c9",
      "scenario/blender/panels.py": "4b3a40ef7555b64709dffa4858ee55b7c2a9b00b6bf22adc348d96f1c5f1b3bc",
      "scenario/blender/props.py": "b79a80e5aeb6e3819cd3c65a4cf0e81e0cdc5777ee34f7a123cc26fe7730fbfe",
      "scenario/blender/shot_planner.py": "1a332a637731b63baeb9e46f9df62c316e441794ea82dd9ea6b6d2496a5018e0",
      "tests/blender/test_model_generation.py": "2e41a94ee2ec97c75f5a9969ff8c1aa044a7bfd9b866f57e432aa310658c368a",
      "tests/blender/test_reference_form.py": "8430e511f1ffd768e6496e73cf6f0b1841360c278736bfe637581abd4ab0de43",
      "tests/blender/test_render_lanes.py": "7dcb39c8a22c6813c1880d906171b88d78d7ece53d14d68529d267132c427332"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
