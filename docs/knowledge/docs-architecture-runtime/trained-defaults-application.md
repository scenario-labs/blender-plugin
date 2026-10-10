---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.trained-defaults-application",
  "title": "Applying trained-model project defaults in the runtime",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "trained-defaults-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the sentences added to the project-selection paragraph: the per-selection cache (RuntimeState.trained_defaults, cleared by trained_models.clear on retirement and checked against the active owner's context_id before drawing reads it); pump._process calling trained_defaults.apply_pending after catalog delivery and before pricing, with an unexpected failure logged once per type instead of stopping the estimate loop; render_commands.request and inspect calling the same step for local MCP, headless included; apply_pending skipping linked scenes, changing only forms without model_key or slots, and repricing a governed form whose price does not show its current reason without repeating requests for hidden lanes; build_request refusing such a form through blocking_reason, which never selects a connection, before its other request checks, so _rearm's comparison with the shown reason cannot reprice the form in a loop; resolve accepting only a base in the form's own model list; render_commands.configure recording a named model_id as model_key before its inspection applies anything; props._find_lane_state marking the edited slot's or parameter's own scene, so applying a default to another scene reprices only that scene's form. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,254 tests (OK, 2 Windows-only skips) with ZIP sha256 5d94b5a727a8b20cf3640b15b1c4446053d79a75905fc79b1f282a84b119298c, whose 148 Python files match git archive of the reviewed fix commit, including the 21 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). Installed tests call apply_pending and one pump._process tick directly (applying a default, then logging a synthetic failure once over two ticks); the bpy.app.timers registration itself was not run. Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality. Five of those tests came from an adversarial review and fail on the previous head: naming the shown render model through MCP, a blocked form not repriced in a loop, a default saved or applied in one scene repricing no other scene, a default refused for a base its form does not list, and a base described without inputs read once.",
    "sources": {
      "scenario/blender/pump.py": "0839e0c312499ae6292db8aaafe7a9a6ebe5fb3d5e3a81c0f773965fa256b96a",
      "scenario/blender/trained_defaults.py": "ccf522bd4326d15d86885bdedeee7fbb44b82b8c086ca9c206c8d9e8356932a6",
      "scenario/blender/render_commands.py": "204bf2aaea232786a470dd7eaad9325c6f1316b6a61d9d99eee6b9fceb64f54f",
      "scenario/blender/generation.py": "339ce612dd6d2dc0fe05478d53f1742ed267f3363465ce4cac68ea4b011c1920",
      "scenario/blender/runtime.py": "0cb590b37bf3593496cd09bb7c9167fab481ad3b49a211a828f1a3677c7368b4",
      "scenario/blender/trained_models.py": "2c4dadd4a0a5ef2216ca00045b43724da50b5fe5bd1c0bcaddf1a471a3642bd9",
      "tests/blender/test_trained_section.py": "cccd18467914ad3e62f00a7e7c302b08b34ceac96f7ded93be59d47c85d9800a",
      "scenario/blender/props.py": "49b6976e43affda255eff6622f3e397d344f001b061e090803d4f6b7f7110746"
    }
  }
}
---

Evidence for [optional project selection](../../architecture/runtime.md#optional-project-selection).
