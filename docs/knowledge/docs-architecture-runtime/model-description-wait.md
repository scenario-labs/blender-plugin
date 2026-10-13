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
    "base_revision": "df2fac37c5e605854718811ffaf74384d8341033",
    "limits": "Reviewed the catalog-delivery sentence on MCP description waits against tools_scenario._after_description, generation.await_description and model_reader with the worker bookkeeping, JobManager.fetch_models returning its worker and the protocol's chained deferred delivery. The worker never reads bpy; it ends after queuing its models event, and the main thread drains that event through process_catalog_events in both the GUI pump and headless MCP calls. The covered paths are model_schema; estimate_cost and generate on every lane, where the render lanes now read the form model's description in render_commands.request before build_request; render_form configure and prepare; and the render-lane estimate_prompt, before the prompt facade quotes. generation.await_description makes a required description raise ModelLoading or its failure. render_form inspect and remove use an optional description: they wait for a read they can start or join, then answer with the form's errors after a failed or expired read, without replacing a recorded failure (ModelLoading.required, generation.waited_for). Every path reads the description before it quotes, submits or changes the form. prepare_result_application with purpose video_first_frame is deliberately unchanged: its review never starts a model read, as test_first_frame_handoff asserts, and requires the Render Video model loaded. Panorama, 3D and edit-3D quotes already read through _body_for and ensure_record; list_models needs no description; workflow tools read workflow metadata and wait on their own task. Installed tests on macOS arm64 Blender 5.1.2 with synthetic SDK transports (exact ZIP SHA-256 7c957c4548d94f4c68e145a3806b188362fbe5c42fb7f0396ec72e0661ebf2b8) cover: a first model_schema and estimate_cost on an uncached model waiting for the read they start while the main thread has nothing queued; a first render_image and render_video estimate_cost and then generate, each on an uncached description, reading it before the quote's metadata read and dry run, and before the paid submission; render_form inspect waiting and then reporting a ready form; inspect answering after a failed read, prepare reading again and reporting the failure, and a later inspect starting no read; the render-lane estimate_prompt reading the description before its dry run; the still-loading text after a shortened wait; a failed read reported and read again on the next call; and the registration of all five waiting tools. These tests failed on the code before each fix (the render-lane ones returned \"ScenarioError: Model not loaded yet\", the look price \"Load the render model before preparing its look\"), the shortened-wait test with an error because no wait bound existed. The full installed suite passed 1,869 tests with 3 skips. The 30-second bound is a chosen limit, not a measured production read time. No live Scenario read, MCP client application, GUI session, Blender 5.0 or 5.2 run, or Linux or Windows run is claimed. Rechecked 2026-10-13 after rebasing onto main df2fac37c with the trained-model MCP work: model_schema and the non-render quote paths now read the description through tools_scenario._described, which calls ensure_record, so ModelLoading still reaches the wait, while a LoRA or composition, or a completed description without inputs, raises WithoutInputs as a final refusal and is never polled; _body_for splits and checks trained inputs after the description and before any quote; render_commands.request and configure apply the project default (trained_defaults.apply_pending, the pump's repeatable step) before the model check and the description wait, and render_form inspect applies it once, before choosing which description to await. The full installed suite then passed 1,937 tests with 3 skips on macOS arm64 Blender 5.1.2 (exact ZIP SHA-256 0f62a68b0e42b3cc662b8d6540073126db265d8083d8d74e10a8ed7a9c5c30c3).",
    "sources": {
      "docs/architecture/runtime.md": "9597b4bf3d4ab111bf6f435257bbbae1ef1e961463f95008e03cf38980606c35",
      "scenario/mcp/tools_scenario.py": "09736196c2bd1926d2cc000a78b6fbaf90fb07c4ee1882a0e616654cfc5b5d4d",
      "scenario/mcp/protocol.py": "7686624495c114548474ef7d388d0795ded70e5e45efc7c0f3271bd540790514",
      "scenario/blender/generation.py": "5450f6b76f27108c6a3eafdbfcc5bd57b4c8ee070e17458b3e17be5aaa15bcd1",
      "scenario/blender/render_commands.py": "5642c4ec43268ff224c388891d183363bf02860d775c24aa4ec313cea46557e5",
      "scenario/core/jobs/manager.py": "ea9d222ffe50ad1df9257e8e89350f78f4f9eecdcd70016e00b809ab71803a91",
      "scenario/mcp/server.py": "2268544089dbab0e37a8ee64544942afb1b0970eab8f32201b13e7d9995e6db1",
      "scenario/blender/pump.py": "3f089aed24304ab270a2218fb8500e312cfb94fdd0ec81e6109f3b893803ec07",
      "tests/blender/helpers.py": "eeb97207eb141176c1d4f76842c0fecfe7f4e8ae5a5fc8f4ba09956c4326d7fc",
      "tests/blender/test_sdk_estimates.py": "a19d09d2c44ea9a940d2c884eec8521ba765dcedf1f9c0a7a5771d3df59dbb98",
      "tests/blender/test_model_generation.py": "6c881c79c65ad95f33950e7e65a0131ae3de700a3f8759ca91be83d2b30dc8e8",
      "tests/blender/test_prompt_tools.py": "a24d579a2ad245be785b058038f23e8a80ed547999c1df0091f719fbe43d5269",
      "tests/blender/test_first_frame_handoff.py": "17d353e42a028bace5b19cdb8bc20846f319b81d245e370624fd9b78762e6cfb",
      "tests/unit/test_mcp_deferred.py": "29f47a77d4cf521f4175a27d9d6739ebdda7d02c9dad33a8722b345a6da7ffee",
      "tests/unit/test_catalog_delivery.py": "ff4ea4ae7307ea342bcabcb6301d966789fedfba25c6c791bb5556b58770f7aa"
    }
  }
}
---

# docs/architecture/runtime.md: model description wait

Evidence for [the canonical document](../../architecture/runtime.md).
