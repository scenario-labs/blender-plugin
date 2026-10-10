---
{
  "type": "Evidence",
  "id": "docs-ui-style.render-reference-preparation",
  "title": "Explicit render reference preparation",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "render-reference-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "65c48337d19c4f93127ad8c5e6f21f5e045f808c",
    "limits": "Inspected explicit native render scene/first-frame slots using the existing typed SDK upload lifecycle and exact quote/submission boundary. Eight added native tests cover prepared render submission once, quote invalidation, guarded scene upload, preadmission cleanup, optional first-frame upload/exclusion late role edits, an empty first-frame file picker and protected single-file result reuse. The exact ZIP SHA256 b36ce7ff2d0b27938724bbd415c1c39322f418c8a6ea8fd8e2b06dc524a6aa3b passes 554 offline native tests each on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. On the preceding ZIP (604200f8efdd2a8b96ad364e067b26d62fb9495794d4707cb0db02859bea7a10), a 5.0.1 desktop probe demonstrated capture/upload control, native text edits, refreshed quote, one mock submission and viewport selection/navigation. It subsequently crashed with a background SQLite job-read traceback; root cause remains unresolved under #263. Subsequent 5.0.1 diagnostic polling/screenshot probes and a 144-second real input/focus/viewport/Generate check on that same preceding ZIP completed cleanly with one mock submission, saved screenshot and unchanged normal profile; these reruns do not establish a crash fix. A 90-second automated desktop probe of the earlier review ZIP (1a4890b14e9a44caff4507104ac3c7906b399999ec54ec8776602bf0cdf33ad0) on Blender 5.2.1 with the normal allocator also completed upload/quote/single mock submission, status polling, screenshot and clean shutdown with the normal profile unchanged; it does not establish keyboard interaction or a crash fix. The legacy result callback now preserves the explicitly chosen video first frame and ready quote, covered by an updated native regression. The final ZIP also passed a Blender 5.1.2 desktop check of the initially empty Render Video file field, native path entry, explicit first-frame upload to an asset, viewport selection/navigation and clean shutdown with the normal profile unchanged. Captures and transport were synthetic, no paid/live call occurred, and other OS/CPU, real encoding, full Render Video generation and release acceptance are not established. Automatic Prompt Spark, non-image result application and Film remain separate work. MCP callers still supply final model parameters directly; this adds no API endpoint, SDK fallback or dependency pin. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: first_frame_enabled also counts a role-tagged first-frame slot that holds an asset without a local file (a saved-image handoff); uploaded slots, removal, changed-path and ordering rules are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/render_references.py": "0f5cf2596e96aed0c8cc8a87d0940c6d2c493005621202ab04838ce82a6a2ff6",
      "scenario/blender/generation.py": "c442d732b2f44156237368dee90d3dddbf5e5dd44e5cb7b19c9e201e91d4dd23",
      "scenario/blender/reference_form.py": "9652fb1aa2644be3fb81bb59ba4d8034f0ea979ae50462701f607daf8d4b420d",
      "scenario/blender/render_lanes.py": "970e193133e97f534df0da917d746b45b1998cdc7da18df67762eef65e2060a9",
      "scenario/blender/panels.py": "4b3a40ef7555b64709dffa4858ee55b7c2a9b00b6bf22adc348d96f1c5f1b3bc",
      "scenario/blender/props.py": "30621d146987bc7bb689f8a9dc670b53035c0b95a244f4fe1dc1619b31de0581",
      "scenario/blender/shot_planner.py": "1a332a637731b63baeb9e46f9df62c316e441794ea82dd9ea6b6d2496a5018e0",
      "tests/blender/test_model_generation.py": "2e41a94ee2ec97c75f5a9969ff8c1aa044a7bfd9b866f57e432aa310658c368a",
      "tests/blender/test_reference_form.py": "8430e511f1ffd768e6496e73cf6f0b1841360c278736bfe637581abd4ab0de43",
      "tests/blender/test_render_lanes.py": "84f4666037972d2bb0b5f2979328a43f68c3c7bb4873c0dba539ad4d301b5dd0",
      "scenario/blender/operators.py": "f999a75ef935d5bd9aed4048e0f00b958372589e969ce39cbfcdb4a46118fd2a"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md).
