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
    "limits": "Reviewed the sentences added to the project-selection paragraph: the per-selection cache (RuntimeState.trained_defaults, cleared by trained_models.clear on retirement and checked against the active owner's context_id before drawing reads it); pump._process calling trained_defaults.apply_pending after catalog delivery and before pricing, with an unexpected failure logged once per type instead of stopping the estimate loop; render_commands.request and inspect calling the same step for local MCP, headless included; apply_pending skipping linked scenes, changing only forms without model_key or slots, and repricing a governed form whose price does not show its current reason without repeating requests for hidden lanes; build_request refusing such a form through blocking_reason, which never selects a connection. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,249 tests (OK, 2 Windows-only skips) with ZIP sha256 269ada4c3673990da2c8735dd8b15f8341c0ad69ed5ef0dc8559d77882a6d8c7, whose 148 Python files match git archive of the reviewed feature commit, including the 16 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). Installed tests call apply_pending and one pump._process tick directly (applying a default, then logging a synthetic failure once over two ticks); the bpy.app.timers registration itself was not run. Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "scenario/blender/pump.py": "0839e0c312499ae6292db8aaafe7a9a6ebe5fb3d5e3a81c0f773965fa256b96a",
      "scenario/blender/trained_defaults.py": "de64246c52dc3107a6892ac9ed0e2a892b4d2a4bcbbd0d3f831f23ec09636648",
      "scenario/blender/render_commands.py": "9551e08bb7a898fc9b0872c98a0a5e699ed9c50bede5e8a6e0c69f8cf273f4de",
      "scenario/blender/generation.py": "38115244a8350c53148761f57ba0e12ea40ebba64db7e9879f1767dcf444d934",
      "scenario/blender/runtime.py": "0cb590b37bf3593496cd09bb7c9167fab481ad3b49a211a828f1a3677c7368b4",
      "scenario/blender/trained_models.py": "2c4dadd4a0a5ef2216ca00045b43724da50b5fe5bd1c0bcaddf1a471a3642bd9",
      "tests/blender/test_trained_section.py": "06de61b3c34d0281161432c8f9b637ada8838c760a3b72d977ff9cfe17e18cbf"
    }
  }
}
---

Evidence for [optional project selection](../../architecture/runtime.md#optional-project-selection).
