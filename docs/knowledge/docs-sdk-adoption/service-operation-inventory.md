---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.service-operation-inventory",
  "title": "docs/SDK_ADOPTION.md: SDK service operation inventory",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "service-operation-inventory",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "2026-10-07 removal review: inspected removal of unused raw Scenario client, catalog, generation, job/asset/upload, Spark/LLM and service transport helpers. Shared SDK methods, named issue-29 extensions, credential-free thumbnail download and versioned identity remain. Reviewed explicit reference/prompt/MCP approvals and shared local data locations for the corrected privacy statements. Obsolete client tests retire with those implementations; SDK contracts, complete-text, upload, scope, transfer and native tests remain. That review claimed no new API exception, retry/dependency change, live provider/OAuth, thumbnail hardening, desktop, legal-policy or full release acceptance. Adjacent UI and platform topics retain their own evidence. Exact SDK-only archive 8d6c57231e35df5fe4349616875efe612de9039720d7b3df11eb014d872e915a passes 1051 installed tests per version on macOS arm64 Blender 5.0.1/5.1.2/5.2.1, with two Windows-only skips and normal profiles unchanged. The locked unit suite passes 3776 tests with one known SDK authentication expected failure. SDK baseline contracts passed before the import relocation and in the resulting suite. 2026-10-09 scoped review of the adapter-only workflow step decision row: approvals use workflows.with_raw_response.user_approval; selections use the named SDK issue #33 workflow_user_selection extension, a new documented API exception with per-request max_retries=0, and the dependency tests flag workflows.user_selection for upgrade review. Re-inspected drift in the SDK adapter, extensions and contract/adapter tests, including the asset library list and search reads, which match their inventory row. Every adapter service call still uses an SDK resource method or a named issue #29/#33 extension; other raw HTTP remains the distinct signed-transfer, thumbnail and loopback MCP protocols, plus developer Blender and wheel downloads. A later rebase review on 33d00b05 re-inspected the drift in every listed source: bulk model summaries (#357) use models.get_bulk through SDKAdapter.models_bulk, mapped in the model catalog row; trained-model classification is local; coordinator asset page and search reads and the MCP asset library and workflow metadata tools go through the shared session's adapter methods; result recovery still reads assets.retrieve; prepared-job cancellation is local and sends no request; smoke material checks and offline-runtime tests add no service call. Raw HTTP in the package and tools remains limited to the named #29/#33 extensions, signed transfers, credential-free thumbnails, the loopback MCP shim and developer Blender and wheel downloads. The archive and unit-suite results above belong to the removal review.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "82d37a4f38b72726ca0060ee0cf66e769cec758f96a166aeeed92580d3fe0a08",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "scenario/core/api/user_agent.py": "810791ca79de710914d6423becf96b5d58b37deba576877c5faf0ad3b2104e2a",
      "scenario/core/api/assets.py": "88d5d6df75cd4586f09e37e4d12b4421a4e4750fb0a64ea3aadfa9de7ae220dd",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/core/api/jobs.py": "de996209f09e892a5b7f8279a2f0a2a69df944438f94bda73c869e0126e671ba",
      "scenario/core/jobs/results.py": "0cf7831eef38f0babd6cba539e0ba93a802f70faf5b53eb44ac34aff7ba98028",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/core/jobs/uploads.py": "0eb0df9afcde2f37fcdba510ada065b489d52be058ab7319362af56be4232bea",
      "scenario/core/jobs/credential_storage.py": "add164599e440041f76f94f9347114d829a0df3ef2e158cf533b8084805da074",
      "scenario/blender/runtime.py": "fb83ceaa622cbbfbea25210d2bb8d480231510d11712f58df34f45f41c13cf59",
      "scenario/blender/prompt_tools.py": "1f465204554e10fae9f0903c84f8f834ba8a492451f1c855bde083cca36527e4",
      "scenario/mcp/tools_scenario.py": "8613fe347b43421261f0462fe3972e777fffb6f35f17f9cd4a26d8b321d25331",
      "tools/smoke_image.py": "683dbd2e8af3d18bd418ba318d2e3f03414bd7bf47486c366c2dd0fe24aff0ba",
      "tools/audit_payloads.py": "518a4d1972faf72298f3dadc5d8656e2b17be67fb31ed3fd93263ff62ffef257",
      "tools/record_fixtures.py": "8a8afcee21fe4ab44be34186d22ed7a825167e6461231d29846bfca4d71840f2",
      "tests/unit/test_scenario_sdk_contract.py": "3b126ec239e38d0e5482c15fafdb93ab3326418e0b3ae966ded3ea3d90d75070",
      "tests/unit/test_sdk_adapter.py": "37e9dcb823c8d199794cddc19c809fbceff6c99eae2823a18b401ecd5df9fbbf",
      "tests/unit/test_prompt_results.py": "1c92e1748f5fa57f0047e4471e7fb95104f8e5efa66628373bf254529ddbb25a",
      "tests/unit/test_asset_download_safety.py": "873bdf49066e74a117eef7f47fd3fb53c5aca879c017085dc50cb20023aa5330",
      "tests/blender/test_offline_runtime.py": "62edfb584b3939380215cf077fce03464b7c30f3a9361b7a76acd3aee0f2835f"
    }
  }
}
---

Evidence for [the canonical document](../../SDK_ADOPTION.md).
