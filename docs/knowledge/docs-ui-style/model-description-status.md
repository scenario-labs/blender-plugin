---
{
  "type": "Evidence",
  "id": "docs-ui-style.model-description-status",
  "title": "Model description loading, failure and retry",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "model-description-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Source-reviewed form, Generate row, composer note, Retry loading model, offline refusal and MCP description reads for lanes without a schema, including a saved model-load error that this session did not record. Native tests patch online access, the catalog and the background read; drawing is checked with a recording layout, not screenshots. The SDK catalog rejects unparseable form schemas before caching. Exact ZIP 514f2daaa93821972c9f536f91d8c3606c3916a7f3b816b42ea761376b36585d passes 1160 installed tests (2 Windows-only skips) on macOS arm64 Blender 5.1.2 only. This does not establish live Scenario failures, desktop focus or interaction, Blender 5.0 or 5.2 runs, or release acceptance. Scoped 2026-10-11 check of the native first-frame control, not a full re-review: render_lanes._draw_first_frame only adds a read-only From a saved result label under a Render Video first-frame slot with intact saved-result provenance, and render_lanes.first_frame_route_lines now supplies the two route lines it already drew for an exclusive first frame; the drawing this topic covers is unchanged. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-13 check of the MCP sentence, not a full re-review: an MCP call needing the description now starts or joins the read and waits for it off the main thread, returning a new failure's reason, instead of reporting a recorded failure once; the sentence was rewritten and checked against tools_scenario._after_description and test_sdk_estimates. test_catalog_delivery only gains a check that fetch_models returns its worker. The form, composer and retry drawing this topic covers is unchanged; the review date and base revision are unchanged.",
    "sources": {
      "docs/UI_STYLE.md": "d373948396c49c54d33c435fed4dbc24dd6393a4b6130e2ad542246ac7d44d0a",
      "scenario/blender/generation.py": "6f73c4ba35ceb97097d1356b2267c5b2b7a2a7105b6900d0376d2604f9e9de8f",
      "scenario/blender/panels.py": "452dca5173123a40e757f37975acae3e7a27e9946a1bb5b9c0f1ef4bd33fcf01",
      "scenario/blender/render_lanes.py": "059119b06a18bcd0083c93dd51f00f923140db33776a2ccb56366e0ad78669b7",
      "scenario/blender/operators.py": "41a8a513e4adec195e56794c7430078a95a46ddc1c48e2e682a24d2ff656512f",
      "scenario/blender/composer/draw.py": "db9ce841a722d8b7761786bd1ea44c6a1d7e189ce0673560d5e604f35a78c0cf",
      "scenario/blender/runtime.py": "43003d6a75ea5b11f2459ba56d39db94d43359a1cd1564765a10471d7979889e",
      "scenario/core/api/sdk_catalog.py": "d2405048078890ff64037a359281ec1413cfd114e8bc599aa9bc29889f9638d3",
      "scenario/core/jobs/manager.py": "f79ea01367faf949a139d7daaeb55ff47e58d86cc98fd58e5ed3c6bcfd6183ab",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_generation.py": "c9304e93cdc701e8878c0837f937a79c51daddb8163c399d10998a655a294ee4",
      "tests/unit/test_sdk_catalog.py": "332f4adfe0a83aac06e9512273b91b1276a2a8b7384b53bc2cb88290254ee67e",
      "tests/unit/test_catalog_delivery.py": "ff4ea4ae7307ea342bcabcb6301d966789fedfba25c6c791bb5556b58770f7aa"
    }
  }
}
---

Supports [the model chooser](../../UI_STYLE.md#the-model-chooser) rules for a form whose model description is loading, failed, unrequested or blocked by disabled online access.
