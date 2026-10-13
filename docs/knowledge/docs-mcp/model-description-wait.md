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
    "base_revision": "8720223989e9b57b8cee7378f44513b838466a5a",
    "limits": "Reviewed the quote-contract paragraph on model descriptions and the still-loading troubleshooting entry against tools_scenario._after_description and its registration; generation.ModelLoading, ensure_record, await_description, waited_for, model_reader and the worker bookkeeping in _start_model_read, request_models, set_models and clear_catalog; JobManager.fetch_models returning its worker; protocol.handle_message continuing a DeferredTool that a finish returns; and ScenarioError text without a status prefix for status 0. The request thread only joins the read's worker; the main thread drains and applies the read before running the tool again, and a failure recorded for a required description is returned without another read. The covered paths are model_schema; estimate_cost and generate on every lane, where the render lanes now read the form model's description in render_commands.request before build_request; render_form configure and prepare; and the render-lane estimate_prompt, before the prompt facade quotes. generation.await_description makes a required description raise ModelLoading or its failure. render_form inspect and remove use an optional description: they wait for a read they can start or join, then answer with the form's errors after a failed or expired read, without replacing a recorded failure (ModelLoading.required, generation.waited_for). Every path reads the description before it quotes, submits or changes the form. prepare_result_application with purpose video_first_frame is deliberately unchanged: its review never starts a model read, as test_first_frame_handoff asserts, and requires the Render Video model loaded. Panorama, 3D and edit-3D quotes already read through _body_for and ensure_record; list_models needs no description; workflow tools read workflow metadata and wait on their own task. Offline unit tests cover the message format, chained deferred work and the worker handle on Python 3.11. Installed tests on macOS arm64 Blender 5.1.2 with synthetic SDK transports (exact ZIP SHA-256 7c957c4548d94f4c68e145a3806b188362fbe5c42fb7f0396ec72e0661ebf2b8) cover: a first model_schema and estimate_cost on an uncached model waiting for the read they start while the main thread has nothing queued; a first render_image and render_video estimate_cost and then generate, each on an uncached description, reading it before the quote's metadata read and dry run, and before the paid submission; render_form inspect waiting and then reporting a ready form; inspect answering after a failed read, prepare reading again and reporting the failure, and a later inspect starting no read; the render-lane estimate_prompt reading the description before its dry run; the still-loading text after a shortened wait; a failed read reported and read again on the next call; and the registration of all five waiting tools. These tests failed on the code before each fix (the render-lane ones returned \"ScenarioError: Model not loaded yet\", the look price \"Load the render model before preparing its look\"), the shortened-wait test with an error because no wait bound existed. The full installed suite passed 1,869 tests with 3 skips. The 30-second bound is a chosen limit, not a measured production read time. No live Scenario read, MCP client application, GUI session, Blender 5.0 or 5.2 run, or Linux or Windows run is claimed. Rechecked 2026-10-13 after rebasing onto main df2fac37c with the trained-model MCP work: model_schema and the non-render quote paths now read the description through tools_scenario._described, which calls ensure_record, so ModelLoading still reaches the wait, while a LoRA or composition, or a completed description without inputs, raises WithoutInputs as a final refusal and is never polled; _body_for splits and checks trained inputs after the description and before any quote; render_commands.request and configure apply the project default (trained_defaults.apply_pending, the pump's repeatable step) before the model check and the description wait, and render_form inspect applies it once, before choosing which description to await. The full installed suite then passed 1,937 tests with 3 skips on macOS arm64 Blender 5.1.2 (exact ZIP SHA-256 0f62a68b0e42b3cc662b8d6540073126db265d8083d8d74e10a8ed7a9c5c30c3). Rechecked 2026-10-13 after rebasing onto main 872022398, which marks the file modified after local MCP scene changes: every description wait and refusal comes before a mark. render_form configure reads the description in its preflight, before the block that marks the form; render_form prepare awaits it before file_state.marking wraps the preparation; inspect and the render-lane request mark nothing. A native test records no mark through waits, failed reads and refusals and exactly one for a configure that waited for its description. The full installed suite then passed 1,991 tests with 3 skips on macOS arm64 Blender 5.1.2 (exact ZIP SHA-256 2f427c0d74fd6326a8ddc0a966640819d19eb03ccb810d3a20c73fdb9d397bdc), including tests/blender/test_file_modified.py.",
    "sources": {
      "docs/MCP.md": "2b43e3e9348b9a95634e922d2ce5e9669885c874050b4e84b95972e5b4accce4",
      "scenario/mcp/tools_scenario.py": "d286fcf60d6d29109ba08e86bd765b927884d5608a64193e94f46e4658d7c92f",
      "scenario/mcp/protocol.py": "7686624495c114548474ef7d388d0795ded70e5e45efc7c0f3271bd540790514",
      "scenario/blender/generation.py": "5450f6b76f27108c6a3eafdbfcc5bd57b4c8ee070e17458b3e17be5aaa15bcd1",
      "scenario/blender/render_commands.py": "226bf4e14692ce5cdfc3447083d16cfe987946b9c434c9361633b0a6b8402b51",
      "scenario/core/jobs/manager.py": "ea9d222ffe50ad1df9257e8e89350f78f4f9eecdcd70016e00b809ab71803a91",
      "scenario/core/api/errors.py": "584c70f20fca386bd18ce69d323a0f746a0f8193c25c9e111f494a4fe8973157",
      "tests/blender/helpers.py": "283317572fdd825a7d9068ea72b876799a1485dc9502d6d2763518e503a0d61d",
      "tests/blender/test_sdk_estimates.py": "a19d09d2c44ea9a940d2c884eec8521ba765dcedf1f9c0a7a5771d3df59dbb98",
      "tests/blender/test_model_generation.py": "ad1107bead6e602435023d1e01b5da4f336f6d08c93527c3f6b57792e60d037b",
      "tests/blender/test_prompt_tools.py": "a24d579a2ad245be785b058038f23e8a80ed547999c1df0091f719fbe43d5269",
      "tests/blender/test_first_frame_handoff.py": "17d353e42a028bace5b19cdb8bc20846f319b81d245e370624fd9b78762e6cfb",
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
