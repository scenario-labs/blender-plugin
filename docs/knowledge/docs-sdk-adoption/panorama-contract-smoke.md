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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Inspected the contract case path in tools/smoke_image.py: contract_body calls SDKAdapter.model, which uses scenario-sdk 2.2.0 models.with_raw_response.retrieve, at quote and again at submit; quotes and the single submission keep JobCoordinator.quote_model and the shared submission (generate.with_raw_response.run_model, dryRun in the query, max_retries=0), unchanged in scenario/core/api/sdk_adapter.py. saved_results builds an SDKAdapter with online=lambda: False and only verifies local receipts, and tools/panorama_report.py reuses it with no SDK call. Offline tests use the real adapter with a mock transport. A zero-spend live quote of two text cases confirmed the model reads and dry runs; no paid request, SDK change or dependency change is claimed. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): the adapter gained other operations (asset organization, workflow step decisions) but SDKAdapter.model, estimate_model and the submission path these cases use are unchanged.",
    "sources": {
      "tools/smoke_image.py": "61e540d79ae9dc743f287199f152707ca183808084e3bc14c6786c07122318f3",
      "tools/panorama_report.py": "71b395184d500a8e5d8325aeb4c9096a8c7b5efc2a37e58e017bdef11c58eb7b",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "tests/unit/test_smoke_panorama.py": "e47f1ed2e594da734b0303ecebee867d0b935198c005a87a9db6643dea7ae42d"
    }
  }
}
---

# SDK adoption: panorama contract model checks

Evidence for [model acceptance commands](../../SDK_ADOPTION.md#model-acceptance-commands).
