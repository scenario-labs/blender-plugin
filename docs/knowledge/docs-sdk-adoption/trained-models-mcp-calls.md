---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-models-mcp-calls",
  "title": "Scenario calls of the local MCP trained-model tools",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-models-mcp-calls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Trained models through local MCP section and the added routes-paragraph sentences. list_models with the trained source reaches the service only through trained_models.request_bases: JobManager.fetch_trained (SDKCatalog.trained_models over SDKAdapter.models with privacy=private, read again only after a failed read) and fetch_base_schemas (SDKCatalog.get, SDKAdapter.model), once per connection. model_schema uses generation.ensure_record, which makes no read for a listed LoRA or composition and none again for a description this connection already read without inputs (WithoutInputs, final), so a trained model_id costs at most one description read. estimate_cost builds the payload locally (trained_models.split_parameters and apply_picks make no request) before the unchanged ModelJobs.quote path with its fresh reads and dry run; generate uses ModelJobs.submit. model_defaults reads and writes the job store through trained_defaults and starts at most the existing generation.request_model read inside resolve. A listed LoRA in the composition input, or a listed composition in the stack input (installed test: no request of any kind for estimate_cost or generate), is refused by apply_picks as a RouteError with the RouteQuoteError text, and the updated installed test_sdk_estimates test shows no MCP read or dry run for it, while the same listed LoRA sent in the stack through MCP is read fresh with the base by the quote and refused with the RouteQuoteError text, with no dry run. The JSON spelling changes come from params.float32_decimal in params_ui.collect_values and the number defaults in tools_scenario._body_for; installed tests show equal dry-run bytes and saved payload_sha256. No SDK method, raw fallback, extension, issue or dependency was added. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,266 tests (OK, 2 Windows-only skips) with ZIP sha256 e62f0acc496aef67a835b014532c94326220640c541d130fe5a36a4632efb9d6, whose 148 Python files match git archive of the reviewed fix commit, including the 12 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality. Re-checked on 2026-10-12 after rebasing the stack onto main c90955dd, whose ff8d29d8 adds the Environment (panorama) lane: tools_scenario._body_for skips the number-default start when a panorama contract applies, so those requests keep the contract's lane defaults (the Flux skybox still quotes numOutputs 1) and send the values main sends; the JSON spelling paragraph names that exception. Main's later workflow-step and preview commits change only workflow and preview rows and paragraphs of this document. The trained-model calls above are unchanged. On main ff8d29d8, with the skip removed, the installed suite on macOS arm64 Blender 5.1.2 failed exactly the two Environment-lane quote tests of test_model_generation; with it, all 1,727 tests passed (3 Windows-only skips). Main's other changes to the listed sources were not re-reviewed here.",
    "sources": {
      "docs/SDK_ADOPTION.md": "9e49e6797db7c5daf059ff95379429c8afa06d6f3b3955e57d6a6ef91760afe5",
      "scenario/mcp/tools_scenario.py": "8c30b3e799a603ddba352f1f88afd6100af8b073acffa808556f627ddc596bda",
      "scenario/blender/trained_models.py": "f3ce308f83794bcf4a4a5ed92525e53b5cb511c235ccdd3f3f97da28f270ab9a",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/blender/params_ui.py": "b7778c8864d26197efa507c0b16f997dedb3a3b6f8a219de439b5d80e056597e",
      "scenario/core/schema/params.py": "5bfbbe9fdf6edcdb376f7671bd5e355188bbef1dc8d3e2c723a50e8b1334025e",
      "scenario/core/jobs/manager.py": "3f63861575bde2e83b74ab3e8982215432b72615f9b00ba220bb3da3673c3080",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "tests/blender/test_mcp_trained_models.py": "9f959cfe352d90fe7fdd1e5606b5c925d043f0fdd02cfdda311b1fd4a1a07375",
      "tests/blender/test_sdk_estimates.py": "5908365ff95966db8c65be63dabe3707f5733932d328be1f32a1f9aac4d3ec55",
      "scenario/blender/generation.py": "17c12bf4ee35dd3e0f15b5fdc9b0038d394330f601160ca1e8eb80b86df99a8b",
      "scenario/core/api/trained_offers.py": "863c3d82fa83b00fe097daf72240367482c4119d2d2f0203f8918dce2c34f1e3"
    }
  }
}
---

Evidence for [trained models through local MCP](../../SDK_ADOPTION.md#trained-models-through-local-mcp).
