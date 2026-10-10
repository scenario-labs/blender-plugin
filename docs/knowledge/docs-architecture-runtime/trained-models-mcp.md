---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.trained-models-mcp",
  "title": "Local MCP over the trained-model runtime",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "trained-models-mcp",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the sentence on local MCP in the active SDK catalog paragraph: list_models with the trained source calls trained_models.request_bases and lists trained_models.offers rows, the rows the picker draws (compared in an installed test, which also shows one base description read shared by both); estimate_cost and render_form build choices through trained_models.apply_picks and checked_choice, both over trained_routes.apply; model_defaults goes through trained_defaults over runtime.ensure_model_defaults. These tools are not marked offthread, so they run on the main thread. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,266 tests (OK, 2 Windows-only skips) with ZIP sha256 e62f0acc496aef67a835b014532c94326220640c541d130fe5a36a4632efb9d6, whose 148 Python files match git archive of the reviewed fix commit, including the 12 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Re-checked on 2026-10-10 after the MCP fix commit (ensure_record, apply_picks, placement_error, _described and model_schema/_body_for): apply_picks still builds MCP choices over trained_routes.apply after its new placement check, and model_schema, estimate_cost and generate still run on the main thread; the claims above still hold. Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/architecture/runtime.md": "9ee1eaf6ac0933c8345962404275c319dee768c598152ba48cd07754c9d14b0b",
      "scenario/mcp/tools_scenario.py": "32962ae1546dd74f80da6a0e4c5ca05c5c403496dd2657341156dc88667825ba",
      "scenario/mcp/protocol.py": "796b929e5858ad287274d3bebf41fc25318ee5862a3df284111e117605b4a4c6",
      "scenario/blender/trained_models.py": "f3ce308f83794bcf4a4a5ed92525e53b5cb511c235ccdd3f3f97da28f270ab9a",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/blender/render_commands.py": "e6888cd27ae5ac6c9593bf61a2e167021f4173d7087059054440f770376c1c17",
      "tests/blender/test_mcp_trained_models.py": "9f959cfe352d90fe7fdd1e5606b5c925d043f0fdd02cfdda311b1fd4a1a07375"
    }
  }
}
---

Evidence for [the active SDK catalog](../../architecture/runtime.md#active-sdk-catalog).
