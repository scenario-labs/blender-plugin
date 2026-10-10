---
{
  "type": "Evidence",
  "id": "docs-mcp.trained-models-mcp",
  "title": "Trained models through local MCP",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "trained-models-mcp",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Trained models (LoRAs and compositions) subsection and the mapping row against the listed sources. list_models with source trained or all (image and render_image only) calls trained_models.request_bases, which reads a failed trained list again and the lane's unknown base descriptions once per connection, then describes trained_models.offers rows with trained_offers.describe_offer: kind, sanitized REST type, private, available or reason, stack or composition routes naming the base and its inputs with the declared scale range, step, default and item limits, composition concepts, and default marks from the lane's saved default; at most 40 rows, with bases progress and a note while reads are pending; offers skips private custom models as the picker does. model_schema adds model_types, min_items/max_items for arrays, roles and lora_component from LoraSlot, or lora_component_error. tools_scenario._body_for splits the base's lorasComponent inputs with trained_models.split_parameters and trained_offers.requested_picks (strict lists, one strength per LoRA with at most 4 decimals, a composition alone), refuses them outside image and render_image, and rebuilds them with trained_models.apply_picks: it needs the loaded trained list (a failed list is not read again there), refuses a listed LoRA in the composition input, a listed composition in the stack input and an explicit strength without a declared range, then calls trained_routes.apply, all before any request; the installed test_sdk_estimates test shows a listed LoRA in the stack still reaching the quote's fresh reads through MCP (RouteQuoteError for a training status, no dry run) and a listed LoRA in the composition input refused with no read. render_commands.configure checks trained picks with trained_models.checked_choice before any change and writes them with replace_choice/write_slots as an explicit choice ([] clears). For equal bytes, params_ui.collect_values sends decimal fields through params.float32_decimal and _body_for starts unset number parameters at their declared default (null still omits one); the installed tests compare form and MCP dry-run bytes for a stack, a composition, a field switched off versus null and a default's parameters, and the two saved intents' payload_sha256 and target after both submissions. generate names the trained choice in job meta like request_meta. model_defaults get/set/clear goes through trained_defaults.load, explicit_default (resolve), store and clear with context and revision checks. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,266 tests (OK, 2 Windows-only skips) with ZIP sha256 e62f0acc496aef67a835b014532c94326220640c541d130fe5a36a4632efb9d6, whose 148 Python files match git archive of the reviewed fix commit, including the 12 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). The fix commit also routes model_schema, estimate_cost and generate through tools_scenario._described: generation.ensure_record raises WithoutInputs, a final ScenarioError with trained_offers.no_inputs_reason text, for a listed LoRA or composition (RuntimeState.trained_records or a public list row) before any read and for a description this connection already read without inputs (SDKCatalog.load_cached), instead of starting another read; _described adds the list_models(source=trained) route text for a LoRA or composition, and the explicit retry operator still reads again through request_model. apply_picks first calls trained_offers.placement_error, which refuses a listed LoRA in the composition input and a listed composition in the stack input (with or without a strength, naming its position and the composition input when the base accepts its type) rather than letting trained_routes.apply move it. Installed tests show listed private and public LoRAs and a composition as model_id refused on repeated model_schema and estimate_cost calls with no request, an unlisted LoRA and a non-trained record without inputs read once and then refused finally, and a composition in loras (alone, with a strength, after a LoRA) refused by estimate_cost and generate with no request; unit tests cover placement_error and no_inputs_reason. Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/MCP.md": "2404e307836da4dce8bda28fbc9f2710432e3f1014d6d87d48e4e6c0ec1fca70",
      "scenario/mcp/tools_scenario.py": "32962ae1546dd74f80da6a0e4c5ca05c5c403496dd2657341156dc88667825ba",
      "scenario/blender/trained_models.py": "f3ce308f83794bcf4a4a5ed92525e53b5cb511c235ccdd3f3f97da28f270ab9a",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/blender/render_commands.py": "e6888cd27ae5ac6c9593bf61a2e167021f4173d7087059054440f770376c1c17",
      "scenario/blender/params_ui.py": "b7778c8864d26197efa507c0b16f997dedb3a3b6f8a219de439b5d80e056597e",
      "scenario/core/api/trained_offers.py": "863c3d82fa83b00fe097daf72240367482c4119d2d2f0203f8918dce2c34f1e3",
      "scenario/core/schema/params.py": "5bfbbe9fdf6edcdb376f7671bd5e355188bbef1dc8d3e2c723a50e8b1334025e",
      "tests/blender/test_mcp_trained_models.py": "9f959cfe352d90fe7fdd1e5606b5c925d043f0fdd02cfdda311b1fd4a1a07375",
      "tests/blender/test_mcp_contracts.py": "d590f39621ceab4a684de2bf65bc8f71b98e0f55b15b82d6ae06ee7978d3fa6e",
      "tests/blender/test_sdk_estimates.py": "5908365ff95966db8c65be63dabe3707f5733932d328be1f32a1f9aac4d3ec55",
      "tests/unit/test_trained_offers.py": "4ab4815ae411df1457d5adae24806983ccd2257b8ebc8dbc75eeb098980798f2",
      "tests/unit/test_params.py": "c7e8a5e11658bba01c78328fed367dbc3aa54ad043291c767b6534e480d51ae7",
      "tests/unit/test_mcp_descriptions.py": "09854b5cb6810670c1e4974421fe3bb7a2bc27b37825c7e4a97cc56b94ae62ee",
      "scenario/blender/generation.py": "17c12bf4ee35dd3e0f15b5fdc9b0038d394330f601160ca1e8eb80b86df99a8b"
    }
  }
}
---

Evidence for [trained models through local MCP](../../MCP.md#trained-models-loras-and-compositions).
