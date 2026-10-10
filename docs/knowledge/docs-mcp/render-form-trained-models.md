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
    "limits": "Reviewed the inspection paragraph of Preparing Render Image and Render Video: render_commands.inspect returns trained_models with each Render Image slot's model ID, kind and strength rounded by trained_models.slot_scale (null without a strength control); render_commands.request and estimate_cost/generate for render lanes use generation.build_request, which writes these slots with trained_models.apply_to, so render quotes and generation include them, and a choice that cannot run returns its reason in errors. render_commands.inspect and request first call trained_defaults.apply_pending for the scene, which writes the selected credentials and project's saved Render Image default into a form without model_key or trained slots once it resolves, or leaves that form blocked with the reason; render_commands.configure records a named model_id as model_key before its inspection, so naming the shown model is an explicit choice the default no longer replaces. No MCP tool chooses or edits the slots or reads, saves or clears defaults; the render_form tool description names the field. Installed tests check the listed and empty cases (test_trained_models), a Render Image default applied through render_form, and configure naming the shown model or naming none (test_trained_section). The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,254 tests (OK, 2 Windows-only skips) with ZIP sha256 5d94b5a727a8b20cf3640b15b1c4446053d79a75905fc79b1f282a84b119298c, whose 148 Python files match git archive of the reviewed fix commit, including the 21 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). Render quote bytes with a trained choice were not compared between UI and MCP in an installed test; both call the same build_request. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "docs/MCP.md": "fae868f78d1ae7fe1fc43c572f99710dd3efb292bd29de34b2525601a60de0ef",
      "scenario/blender/render_commands.py": "204bf2aaea232786a470dd7eaad9325c6f1316b6a61d9d99eee6b9fceb64f54f",
      "scenario/blender/trained_models.py": "2c4dadd4a0a5ef2216ca00045b43724da50b5fe5bd1c0bcaddf1a471a3642bd9",
      "scenario/blender/generation.py": "339ce612dd6d2dc0fe05478d53f1742ed267f3363465ce4cac68ea4b011c1920",
      "scenario/mcp/tools_scenario.py": "f75442a1f4f93f33bee636109813a1f070f27aa47b5d21013887cd9854bc8326",
      "tests/blender/test_trained_models.py": "405c8e7b43ba0228ede4f6d31fbc2d89c93cdb031b33622dd492e5c689382a14",
      "scenario/blender/trained_defaults.py": "ccf522bd4326d15d86885bdedeee7fbb44b82b8c086ca9c206c8d9e8356932a6",
      "tests/blender/test_trained_section.py": "cccd18467914ad3e62f00a7e7c302b08b34ceac96f7ded93be59d47c85d9800a"
    }
  }
}
---

Evidence for [the canonical guide](../../MCP.md).
