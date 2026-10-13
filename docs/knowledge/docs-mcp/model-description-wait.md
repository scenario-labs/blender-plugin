---
{
  "type": "Evidence",
  "id": "docs-mcp.model-description-wait",
  "title": "docs/MCP.md: model description wait",
  "description": "How MCP tools that need a model description wait for its read instead of failing.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "model-description-wait",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed the quote-contract paragraph on model descriptions and the still-loading troubleshooting entry against tools_scenario._after_description and its registration for model_schema, render_form, estimate_cost and generate; generation.ModelLoading, ensure_record, model_reader and the worker bookkeeping in _start_model_read, request_models, set_models and clear_catalog; JobManager.fetch_models returning its worker; protocol.handle_message continuing a DeferredTool that a finish returns; and ScenarioError text without a status prefix for status 0. The request thread only joins the read's worker; the main thread drains and applies the read before running the tool again. model_schema and estimate_cost read the description before quoting, render_form configure before changing the form, and generate before submitting; its earlier quote lookup is read-only. A failure recorded for the awaited read is returned without starting another read. Offline unit tests cover the message format, chained deferred work and the worker handle on Python 3.11. Installed tests on macOS arm64 Blender 5.1.2 with the synthetic SDK transport (exact ZIP SHA-256 190a8dce062942b744c0b91c5a36f07cf20116976bdb11ff5cb40bb2cccc7d7a) cover a first model_schema and a first estimate_cost for a model without a cached description: each waits for the read it starts while the main thread has nothing queued, then answers, and the estimate makes its own metadata read and dry run after the description read. A read still in flight after a shortened wait returns the still-loading text with no quote or dry run, and the next call answers without reading again. A failed read returns its sanitized reason and the next call reads again. A registration check covers all four tools. These tests failed on the unfixed code, the shortened-wait test with an error because no wait bound existed. The full installed suite passed 1,866 tests with 3 skips. The render_form and generate waits rest on source review and the registration check. The 30-second bound is a chosen limit, not a measured production read time. No live Scenario read, MCP client application, GUI session, Blender 5.0 or 5.2 run, or Linux or Windows run is claimed.",
    "sources": {
      "docs/MCP.md": "f2d2c5ba998a75dd4a6f44308b4495ae536d67a5f6484f7ae406bbe5f5467249",
      "scenario/mcp/tools_scenario.py": "624892b941651a99bd584ba78a06bd61b6eb0b85ac993b3b5f815ef9a289208b",
      "scenario/mcp/protocol.py": "7686624495c114548474ef7d388d0795ded70e5e45efc7c0f3271bd540790514",
      "scenario/blender/generation.py": "5c6e2afb7e76d33f6405edb892f16b2d0013940a11eea922c3683cb36c5d3ae9",
      "scenario/core/jobs/manager.py": "ea9d222ffe50ad1df9257e8e89350f78f4f9eecdcd70016e00b809ab71803a91",
      "scenario/core/api/errors.py": "584c70f20fca386bd18ce69d323a0f746a0f8193c25c9e111f494a4fe8973157",
      "tests/blender/test_sdk_estimates.py": "15b1faee42f402b40ecc181c2de9c0793da6a7e67b85641cb349df27261487da",
      "tests/unit/test_mcp_deferred.py": "29f47a77d4cf521f4175a27d9d6739ebdda7d02c9dad33a8722b345a6da7ffee",
      "tests/unit/test_catalog_delivery.py": "ff4ea4ae7307ea342bcabcb6301d966789fedfba25c6c791bb5556b58770f7aa",
      "tests/unit/test_api_errors.py": "1c354389e71cadf59908d3d256c5844ab94840555c22cf358af7f37f21089504",
      "tests/unit/test_mcp_protocol.py": "3b5a5a6d2123f6096fd700640d633eba00445ffcf29e3332f6cfb66b26bd0176"
    }
  }
}
---

# docs/MCP.md: model description wait

Evidence for [the canonical document](../../MCP.md).
