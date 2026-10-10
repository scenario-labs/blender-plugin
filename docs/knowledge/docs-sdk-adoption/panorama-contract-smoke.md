---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.panorama-contract-smoke",
  "title": "SDK adoption: panorama contract model checks",
  "description": "Contract cases add model reads through the shared adapter; saved inputs and the report stay offline.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "panorama-contract-smoke",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the contract case path in tools/smoke_image.py: contract_body calls SDKAdapter.model, which uses scenario-sdk 2.2.0 models.with_raw_response.retrieve, at quote and again at submit; quotes and the single submission keep JobCoordinator.quote_model and the shared submission (generate.with_raw_response.run_model, dryRun in the query, max_retries=0), unchanged in scenario/core/api/sdk_adapter.py. saved_results builds an SDKAdapter with online=lambda: False and only verifies local receipts, and tools/panorama_report.py reuses it with no SDK call. Offline tests use the real adapter with a mock transport. A zero-spend live quote of two text cases confirmed the model reads and dry runs; no paid request, SDK change or dependency change is claimed.",
    "sources": {
      "tools/smoke_image.py": "9e9da23fcfb42eca4d379004d1b55a6bc6d57c25080d1fdd1a3d1b3ed39ff32a",
      "tools/panorama_report.py": "343c70afe583f100c373263fe2d4ed97835ac6fabe09e1edbfe8b9e1edc4f781",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/unit/test_smoke_panorama.py": "f82108630c3bde6db2f170ff82952a3d33ccd16b0bc05eac1e8566c0f0be75ef"
    }
  }
}
---

# SDK adoption: panorama contract model checks

Evidence for [model acceptance commands](../../SDK_ADOPTION.md#model-acceptance-commands).
