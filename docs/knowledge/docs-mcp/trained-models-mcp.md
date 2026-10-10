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
    "limits": "Reviewed the Trained models (LoRAs and compositions) subsection and the mapping row against the listed sources. list_models with source trained or all (image and render_image only) calls trained_models.request_bases, which reads a failed trained list again and the lane's unknown base descriptions once per connection, then describes trained_models.offers rows with trained_offers.describe_offer: kind, sanitized REST type, private, available or reason, stack or composition routes naming the base and its inputs with the declared scale range, step, default and item limits, composition concepts, and default marks from the lane's saved default; at most 40 rows, with bases progress and a note while reads are pending; offers skips private custom models as the picker does. model_schema adds model_types, min_items/max_items for arrays, roles and lora_component from LoraSlot, or lora_component_error. tools_scenario._body_for splits the base's lorasComponent inputs with trained_models.split_parameters and trained_offers.requested_picks (strict lists, one strength per LoRA with at most 4 decimals, a composition alone), refuses them outside image and render_image, and rebuilds them with trained_models.apply_picks: it needs the loaded trained list (a failed list is not read again there), refuses a listed LoRA in the composition input and an explicit strength without a declared range, then calls trained_routes.apply, all before any request; the installed test_sdk_estimates test shows a listed LoRA in the stack still reaching the quote's fresh reads through MCP (RouteQuoteError for a training status, no dry run) and a listed LoRA in the composition input refused with no read. render_commands.configure checks trained picks with trained_models.checked_choice before any change and writes them with replace_choice/write_slots as an explicit choice ([] clears). For equal bytes, params_ui.collect_values sends decimal fields through params.float32_decimal and _body_for starts unset number parameters at their declared default (null still omits one); the installed tests compare form and MCP dry-run bytes for a stack, a composition, a field switched off versus null and a default's parameters, and the two saved intents' payload_sha256 and target after both submissions. generate names the trained choice in job meta like request_meta. model_defaults get/set/clear goes through trained_defaults.load, explicit_default (resolve), store and clear with context and revision checks. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,264 tests (OK, 2 Windows-only skips) with ZIP sha256 9ab6d1987812e12a721b7ed8bc3e91e693cd8e6c4249f4dfc4bde7628a3525c0, whose 148 Python files match git archive of the reviewed head (its scenario package is unchanged since the implementation commit), including the 10 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/MCP.md": "4db0225d41694ad4b55bef05d65e35d72ae8cf10dcf531b133eb0ad1fb7be182",
      "scenario/mcp/tools_scenario.py": "9b0e2dd87ff708889636525124c4a1eb935a45e56983f9138872742717d067db",
      "scenario/blender/trained_models.py": "9b54ff883bc36fdecdd7ddb4e29669cee786722204ec611899d89b1f0a703ba5",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/blender/render_commands.py": "e6888cd27ae5ac6c9593bf61a2e167021f4173d7087059054440f770376c1c17",
      "scenario/blender/params_ui.py": "b7778c8864d26197efa507c0b16f997dedb3a3b6f8a219de439b5d80e056597e",
      "scenario/core/api/trained_offers.py": "71d3baf15c1e92212f159e31a432d20e2e8b2a0228c126df6e0b0c072952c4d0",
      "scenario/core/schema/params.py": "5bfbbe9fdf6edcdb376f7671bd5e355188bbef1dc8d3e2c723a50e8b1334025e",
      "tests/blender/test_mcp_trained_models.py": "19be55835046a01f521c9df0be18ee286f6d58ab1cf3a744209e2a54fcf8ea5a",
      "tests/blender/test_mcp_contracts.py": "d590f39621ceab4a684de2bf65bc8f71b98e0f55b15b82d6ae06ee7978d3fa6e",
      "tests/blender/test_sdk_estimates.py": "5908365ff95966db8c65be63dabe3707f5733932d328be1f32a1f9aac4d3ec55",
      "tests/unit/test_trained_offers.py": "9ee27b6ef294f1564778a1d14db0d86de3673db3ce64ed9da7a844221286bc87",
      "tests/unit/test_params.py": "c7e8a5e11658bba01c78328fed367dbc3aa54ad043291c767b6534e480d51ae7",
      "tests/unit/test_mcp_descriptions.py": "09854b5cb6810670c1e4974421fe3bb7a2bc27b37825c7e4a97cc56b94ae62ee"
    }
  }
}
---

Evidence for [trained models through local MCP](../../MCP.md#trained-models-loras-and-compositions).
