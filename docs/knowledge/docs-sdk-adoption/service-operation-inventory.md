---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.service-operation-inventory",
  "title": "docs/SDK_ADOPTION.md: SDK service operation inventory",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "service-operation-inventory",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03b070b9cb663b63cf8a411f6126efb40d4c66d0",
    "limits": "Inspected removal of unused raw Scenario client, catalog, generation, job/asset/upload, Spark/LLM and service transport helpers. Shared SDK methods, named issue-29 extensions, credential-free thumbnail download and versioned identity remain. Reviewed explicit reference/prompt/MCP approvals and shared local data locations for the corrected privacy statements. Obsolete client tests retire with those implementations; SDK contracts, complete-text, upload, scope, transfer and native tests remain. No new API exception, retry/dependency change, live provider/OAuth, thumbnail hardening, desktop, legal-policy or full release acceptance is claimed. Adjacent UI and platform topics retain their own evidence. Exact SDK-only archive 8d6c57231e35df5fe4349616875efe612de9039720d7b3df11eb014d872e915a passes 1051 installed tests per version on macOS arm64 Blender 5.0.1/5.1.2/5.2.1, with two Windows-only skips and normal profiles unchanged. The locked unit suite passes 3776 tests with one known SDK authentication expected failure. SDK baseline contracts passed before the import relocation and in the resulting suite.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "28f759aeaa504bdcb435ff26dbf5fe8515b32c49d20b770467157fd0d0012735",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/api/sdk_extensions.py": "dc084216172a704ab1453811f9e2c9c1b9755af55fee7c2fa305704449b9a369",
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
      "tests/unit/test_scenario_sdk_contract.py": "3b2b866d7bf0c816c3108b0ad9f6322e95cdc9808627c015917f591250d5371c",
      "tests/unit/test_sdk_adapter.py": "f9df4ef657e0c4ab76e72bfe80ede1ea8bf0a0b9c3026579332603035a1bc7f5",
      "tests/unit/test_prompt_results.py": "1c92e1748f5fa57f0047e4471e7fb95104f8e5efa66628373bf254529ddbb25a",
      "tests/unit/test_asset_download_safety.py": "873bdf49066e74a117eef7f47fd3fb53c5aca879c017085dc50cb20023aa5330",
      "tests/blender/test_offline_runtime.py": "12b3d674dcceffa63b80bf6c7296b01d4558145669d2c8eca0c44da6b78fde42"
    }
  }
}
---

Evidence for [the canonical document](../../SDK_ADOPTION.md).
