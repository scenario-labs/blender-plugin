---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.trained-defaults-application",
  "title": "Applying trained-model project defaults in the runtime",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "trained-defaults-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed the sentences added to the project-selection paragraph: the per-selection cache (RuntimeState.trained_defaults, cleared by trained_models.clear on retirement and checked against the active owner's context_id before drawing reads it); pump._process calling trained_defaults.apply_pending after catalog delivery and before pricing, with an unexpected failure logged once per type instead of stopping the estimate loop; render_commands.request and inspect calling the same step for local MCP, headless included; apply_pending skipping linked scenes, changing only forms without model_key or slots, and repricing a governed form whose price does not show its current reason without repeating requests for hidden lanes; build_request refusing such a form through blocking_reason, which never selects a connection, before its other request checks, so _rearm's comparison with the shown reason cannot reprice the form in a loop; resolve accepting only a base in the form's own model list; render_commands.configure recording a named model_id as model_key before its inspection applies anything; props._find_lane_state marking the edited slot's or parameter's own scene, so applying a default to another scene reprices only that scene's form. Re-reviewed all of these on 2026-10-12 after rebasing onto main 72c5340c, together with the new clause that automatic application does not tag the scene: apply_pending calls _apply with seed, which stores the model enum index (each item's index, as generation.restore_model_key does) and each LoRA strength clamped to its bounds (trained_models.write_slots with seed) as raw ID properties, runs generation.on_model_changed itself and re-arms the price, while Use keeps RNA assignments, which tag the scene only for a different base model or a LoRA strength (re-reviewed again on 2026-10-12: a composition used on the form's current base writes only the trained list and still re-arms the form's price). The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,468 tests (OK, 3 Windows-only skips) with ZIP sha256 a204f42f293554ad18a3f2ccc85cc2aa5046e04f46aa5de2037843c2bad44170, whose 164 Python files match this change's scenario/ sources, including the 23 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). One of them keeps job-session origins captured in two scenes current while apply_pending applies a default there and shows that a Use assigning a different base invalidates one; it failed before the raw writes. Another shows that on the form's current base a stack's Use invalidates origins through its strengths while a composition's Use leaves them current, and that both reprice the form and clear its estimate key. Installed tests call apply_pending and one pump._process tick directly (applying a default, then logging a synthetic failure once over two ticks); the bpy.app.timers registration itself was not run. Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality. Five tests came from an earlier adversarial review and failed on the head before its fixes: naming the shown render model through MCP, a blocked form not repriced in a loop, a default saved or applied in one scene repricing no other scene, a default refused for a base its form does not list, and a base described without inputs read once.",
    "sources": {
      "scenario/blender/pump.py": "80ec5e87d90a6f0d0b336ff4474a77bb34fc68238d151542e3170c7b886caf37",
      "scenario/blender/trained_defaults.py": "df72a33f70df469e124a16a65221a4a919e145ff24529cd3eaaa864a5e771ed8",
      "scenario/blender/render_commands.py": "87864f3b6a908a068daabe2aac0bc5882c12f861bb84ff60b32101a029aff319",
      "scenario/blender/generation.py": "d00e21459c5a0c9a8757e5ed53fc829c3a5d7002797d50e7d69b6d0db712d566",
      "scenario/blender/runtime.py": "3f0ebccb3fa9b1e11b03624638346f8d365a95f6be8a42a6ee1a9e191c356de1",
      "scenario/blender/trained_models.py": "36f16dd75a5cf822bae5be7387c48aad1daa15ed837d2244255661a8f44545f7",
      "tests/blender/test_trained_section.py": "c0e2338e7c172c836d67d97ef9f1beee471e77e4be9824e9659631c245ab6eeb",
      "scenario/blender/props.py": "1d43b48ce3c6a268cc478077f107c9b3625efd61d14cd624f208cba58fc28051"
    }
  }
}
---

Evidence for [optional project selection](../../architecture/runtime.md#optional-project-selection).
