---
{
  "type": "Evidence",
  "id": "docs-mcp.render-form-trained-models",
  "title": "Trained models in render_form inspection",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "render-form-trained-models",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the inspection sentence of Preparing Render Image and Render Video: render_commands.inspect returns trained_models with each Render Image slot's model ID, kind and strength rounded by trained_models.slot_scale (null without a strength control); render_commands.request and estimate_cost/generate for render lanes use generation.build_request, which writes these slots with trained_models.apply_to, so render quotes and generation include them, and a choice that cannot run returns its reason in errors. No MCP tool adds, changes or removes these slots; the render_form tool description names the field. An installed test checks the listed and empty cases through tools_scenario.render_form. The installed suite on macOS arm64 Blender 5.1.2 passed 1,233 tests (2 Windows-only skips), including the 18 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records. Render quote bytes with a trained choice were not compared between UI and MCP in an installed test; both call the same build_request. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "docs/MCP.md": "d6269c7703df1015ee933c42bb2e18262b054fdf5d21ffffa5ca9b08ceb1dac5",
      "scenario/blender/render_commands.py": "5e7646319cd085756abd114cb23cea4888fdb1af37a913d7f0f57ba9d1244f6b",
      "scenario/blender/trained_models.py": "b22065b710995723e43a954910245edc7033710a00dceee93e8000c15023b654",
      "scenario/blender/generation.py": "599f62901fc5a23dfcfd12afb862f983435651a52df2faf3e7f579310f05e122",
      "scenario/mcp/tools_scenario.py": "f75442a1f4f93f33bee636109813a1f070f27aa47b5d21013887cd9854bc8326",
      "tests/blender/test_trained_models.py": "cdc0dad13557080489a7b8957cf6dd2ab73f1dd534c90460650fa5d1b4458f9d"
    }
  }
}
---

Evidence for [the canonical guide](../../MCP.md).
