---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.model-description-wait",
  "title": "docs/architecture/runtime.md: model description wait",
  "description": "Where an MCP call waits for a model description read and where the read is delivered.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "model-description-wait",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed the catalog-delivery sentence on MCP description waits against tools_scenario._after_description, generation.model_reader and the worker bookkeeping, JobManager.fetch_models returning its worker and the protocol's chained deferred delivery. The worker never reads bpy; it ends after queuing its models event, and the main thread drains that event through process_catalog_events in both the GUI pump and headless MCP calls. Installed tests on macOS arm64 Blender 5.1.2 with the synthetic SDK transport (exact ZIP SHA-256 190a8dce062942b744c0b91c5a36f07cf20116976bdb11ff5cb40bb2cccc7d7a) cover a first model_schema and a first estimate_cost for a model without a cached description: each waits for the read it starts while the main thread has nothing queued, then answers, and the estimate makes its own metadata read and dry run after the description read. A read still in flight after a shortened wait returns the still-loading text with no quote or dry run, and the next call answers without reading again. A failed read returns its sanitized reason and the next call reads again. A registration check covers all four tools. These tests failed on the unfixed code, the shortened-wait test with an error because no wait bound existed. The full installed suite passed 1,866 tests with 3 skips. The render_form and generate waits rest on source review and the registration check. The 30-second bound is a chosen limit, not a measured production read time. No live Scenario read, MCP client application, GUI session, Blender 5.0 or 5.2 run, or Linux or Windows run is claimed.",
    "sources": {
      "docs/architecture/runtime.md": "8ce18efd41953d8079848e7303dbfc6ff41ea7850cb95dbb4da65bae988764fe",
      "scenario/mcp/tools_scenario.py": "624892b941651a99bd584ba78a06bd61b6eb0b85ac993b3b5f815ef9a289208b",
      "scenario/mcp/protocol.py": "7686624495c114548474ef7d388d0795ded70e5e45efc7c0f3271bd540790514",
      "scenario/mcp/server.py": "2268544089dbab0e37a8ee64544942afb1b0970eab8f32201b13e7d9995e6db1",
      "scenario/blender/generation.py": "5c6e2afb7e76d33f6405edb892f16b2d0013940a11eea922c3683cb36c5d3ae9",
      "scenario/blender/pump.py": "d099a1dc2e889bd4defa963c8e9c787f0b2f66e0e65e2b4736212725dac3299f",
      "scenario/core/jobs/manager.py": "ea9d222ffe50ad1df9257e8e89350f78f4f9eecdcd70016e00b809ab71803a91",
      "tests/blender/test_sdk_estimates.py": "15b1faee42f402b40ecc181c2de9c0793da6a7e67b85641cb349df27261487da",
      "tests/unit/test_mcp_deferred.py": "29f47a77d4cf521f4175a27d9d6739ebdda7d02c9dad33a8722b345a6da7ffee",
      "tests/unit/test_catalog_delivery.py": "ff4ea4ae7307ea342bcabcb6301d966789fedfba25c6c791bb5556b58770f7aa"
    }
  }
}
---

# docs/architecture/runtime.md: model description wait

Evidence for [the canonical document](../../architecture/runtime.md).
