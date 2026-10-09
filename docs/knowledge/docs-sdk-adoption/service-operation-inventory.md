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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "2026-10-07 removal review: inspected removal of unused raw Scenario client, catalog, generation, job/asset/upload, Spark/LLM and service transport helpers. Shared SDK methods, named issue-29 extensions, credential-free thumbnail download and versioned identity remain. Reviewed explicit reference/prompt/MCP approvals and shared local data locations for the corrected privacy statements. Obsolete client tests retire with those implementations; SDK contracts, complete-text, upload, scope, transfer and native tests remain. That review claimed no new API exception, retry/dependency change, live provider/OAuth, thumbnail hardening, desktop, legal-policy or full release acceptance. Adjacent UI and platform topics retain their own evidence. Exact SDK-only archive 8d6c57231e35df5fe4349616875efe612de9039720d7b3df11eb014d872e915a passes 1051 installed tests per version on macOS arm64 Blender 5.0.1/5.1.2/5.2.1, with two Windows-only skips and normal profiles unchanged. The locked unit suite passes 3776 tests with one known SDK authentication expected failure. SDK baseline contracts passed before the import relocation and in the resulting suite. 2026-10-09 scoped review of the adapter-only workflow step decision row: approvals use workflows.with_raw_response.user_approval; selections use the named SDK issue #33 workflow_user_selection extension, a new documented API exception with per-request max_retries=0, and the dependency tests flag workflows.user_selection for upgrade review. Re-inspected drift in the SDK adapter, extensions and contract/adapter tests, including the asset library list and search reads, which match their inventory row. Every adapter service call still uses an SDK resource method or a named issue #29/#33 extension; other raw HTTP remains the distinct signed-transfer, thumbnail and loopback MCP protocols, plus developer Blender and wheel downloads. Later drift in the results, coordinator, Blender runtime, MCP tools, smoke and offline-runtime sources was not re-reviewed and remains an inspection request. The archive and unit-suite results above belong to the removal review.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "1104fbb8a78b13deafd3c5098d932da39a8fdfa9ee38707e7a96452ec72877a5",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "scenario/core/api/user_agent.py": "810791ca79de710914d6423becf96b5d58b37deba576877c5faf0ad3b2104e2a",
      "scenario/core/api/assets.py": "88d5d6df75cd4586f09e37e4d12b4421a4e4750fb0a64ea3aadfa9de7ae220dd",
      "scenario/core/api/catalog.py": "7a082b55f054ef3105e94f4a9e450ad321c5867a7b6cc178810160db51c64a8f",
      "scenario/core/api/jobs.py": "de996209f09e892a5b7f8279a2f0a2a69df944438f94bda73c869e0126e671ba",
      "scenario/core/jobs/results.py": "d1e9ae96786d9bfaf92f8e1eddc5a0ca467a3b6e834e99f0c4633ffb4d32c15f",
      "scenario/core/jobs/coordinator.py": "026ec2802838c67969dfe54da6fa2a32ae59a28bcc0b5bf587e7831697899a41",
      "scenario/core/jobs/uploads.py": "0eb0df9afcde2f37fcdba510ada065b489d52be058ab7319362af56be4232bea",
      "scenario/core/jobs/credential_storage.py": "add164599e440041f76f94f9347114d829a0df3ef2e158cf533b8084805da074",
      "scenario/blender/runtime.py": "f85b53a9684831297fc07b6715d3286169c2713dc1116bbdb8220a979dcefe4f",
      "scenario/blender/prompt_tools.py": "1f465204554e10fae9f0903c84f8f834ba8a492451f1c855bde083cca36527e4",
      "scenario/mcp/tools_scenario.py": "1d613605107ee7db59790faec37e8a3bd4ee8a014c38b00e0b44be20b67f12c3",
      "tools/smoke_image.py": "fc9d8b8494e8a125908702c9c09f72129f6aeb46ce91b21e5a67bb8b8ed63c9b",
      "tools/audit_payloads.py": "518a4d1972faf72298f3dadc5d8656e2b17be67fb31ed3fd93263ff62ffef257",
      "tools/record_fixtures.py": "8a8afcee21fe4ab44be34186d22ed7a825167e6461231d29846bfca4d71840f2",
      "tests/unit/test_scenario_sdk_contract.py": "a23b96b3792abb83fbca65f0755e7d7c33cec08cd3f739f8cf0dc67e16ffc026",
      "tests/unit/test_sdk_adapter.py": "5ed5648c2487ff6a4ffdf0f4ef8cde0fd20b1363c5ff66d9000e932229fdb23c",
      "tests/unit/test_prompt_results.py": "1c92e1748f5fa57f0047e4471e7fb95104f8e5efa66628373bf254529ddbb25a",
      "tests/unit/test_asset_download_safety.py": "873bdf49066e74a117eef7f47fd3fb53c5aca879c017085dc50cb20023aa5330",
      "tests/blender/test_offline_runtime.py": "12b3d674dcceffa63b80bf6c7296b01d4558145669d2c8eca0c44da6b78fde42"
    }
  }
}
---

Evidence for [the canonical document](../../SDK_ADOPTION.md).
