---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-models-mcp-calls",
  "title": "Scenario calls of the local MCP trained-model tools",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-models-mcp-calls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Trained models through local MCP section and the added routes-paragraph sentences. list_models with the trained source reaches the service only through trained_models.request_bases: JobManager.fetch_trained (SDKCatalog.trained_models over SDKAdapter.models with privacy=private, read again only after a failed read) and fetch_base_schemas (SDKCatalog.get, SDKAdapter.model), once per connection. model_schema uses generation.ensure_record. estimate_cost builds the payload locally (trained_models.split_parameters and apply_picks make no request) before the unchanged ModelJobs.quote path with its fresh reads and dry run; generate uses ModelJobs.submit. model_defaults reads and writes the job store through trained_defaults and starts at most the existing generation.request_model read inside resolve. A listed LoRA in the composition input is refused by apply_picks as a RouteError with the RouteQuoteError text, and the updated installed test_sdk_estimates test shows no MCP read or dry run for it. The JSON spelling changes come from params.float32_decimal in params_ui.collect_values and the number defaults in tools_scenario._body_for; installed tests show equal dry-run bytes and saved payload_sha256. No SDK method, raw fallback, extension, issue or dependency was added. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,264 tests (OK, 2 Windows-only skips) with ZIP sha256 d64765ad8f515f272d21c3fdb9b4f04645d43b053f4f86355d741915cb65e16c, whose 148 Python files match git archive of the reviewed implementation commit, including the 10 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/SDK_ADOPTION.md": "8b8c646b3cf3718ddbc2953d9590e7ca5381debbfec736d9c89bc59e12c8600e",
      "scenario/mcp/tools_scenario.py": "9b0e2dd87ff708889636525124c4a1eb935a45e56983f9138872742717d067db",
      "scenario/blender/trained_models.py": "9b54ff883bc36fdecdd7ddb4e29669cee786722204ec611899d89b1f0a703ba5",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/blender/params_ui.py": "b7778c8864d26197efa507c0b16f997dedb3a3b6f8a219de439b5d80e056597e",
      "scenario/core/schema/params.py": "5bfbbe9fdf6edcdb376f7671bd5e355188bbef1dc8d3e2c723a50e8b1334025e",
      "scenario/core/jobs/manager.py": "3f63861575bde2e83b74ab3e8982215432b72615f9b00ba220bb3da3673c3080",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "tests/blender/test_mcp_trained_models.py": "19be55835046a01f521c9df0be18ee286f6d58ab1cf3a744209e2a54fcf8ea5a",
      "tests/blender/test_sdk_estimates.py": "962644779b97890390178fca9e0df2bb42629053f0eb1af73b1e93190fadf52f"
    }
  }
}
---

Evidence for [trained models through local MCP](../../SDK_ADOPTION.md#trained-models-through-local-mcp).
