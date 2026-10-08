---
{
  "type": "Evidence",
  "id": "docs-privacy.service-operation-inventory",
  "title": "docs/PRIVACY.md: SDK service operation inventory",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "service-operation-inventory",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03b070b9cb663b63cf8a411f6126efb40d4c66d0",
    "limits": "Inspected explicit native reference uploads, prompt quote/approval, MCP generation approval, retired prototype recovery, SDK authorization/User-Agent and shared local data paths for the corrected privacy statements. Shared SDK and storage transfers remain separate from thumbnail requests; the latter still lack per-retry online permission checks. Does not audit external service privacy terms, establish live/paid or desktop acceptance, encrypt local data, or refresh unrelated clipboard/update implementation evidence.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "28f759aeaa504bdcb435ff26dbf5fe8515b32c49d20b770467157fd0d0012735",
      "scenario/core/api/user_agent.py": "810791ca79de710914d6423becf96b5d58b37deba576877c5faf0ad3b2104e2a",
      "scenario/core/api/assets.py": "88d5d6df75cd4586f09e37e4d12b4421a4e4750fb0a64ea3aadfa9de7ae220dd",
      "scenario/core/jobs/credential_storage.py": "add164599e440041f76f94f9347114d829a0df3ef2e158cf533b8084805da074",
      "scenario/core/jobs/upload_store.py": "3b8be69ce6abb8593e7eb28b56403574b6a95534d8c9adf46564bb4941cc502c",
      "scenario/core/jobs/transfers.py": "658d5cd1182e5e7d718fe5b49232da1d6711eb37ab6b548ca5cb21139e194eb6",
      "scenario/core/jobs/upload_transfers.py": "262f2e57734493cd9b21e9d582ec964cf7dbb4ce9688aa1f1a39b17945b3d7d5",
      "scenario/blender/runtime.py": "f85b53a9684831297fc07b6715d3286169c2713dc1116bbdb8220a979dcefe4f",
      "scenario/blender/generation.py": "00d8436fbb222e8464d1b14c9d062f3d513914883edfdaa1b4ed261a1d6f1e02",
      "scenario/blender/reference_form.py": "9652fb1aa2644be3fb81bb59ba4d8034f0ea979ae50462701f607daf8d4b420d",
      "scenario/blender/reference_uploads.py": "00aec147e040a08dd1e79deb7a4cece57fcf6e21fff277b11f25ba62acabf607",
      "scenario/blender/prompt_tools.py": "1f465204554e10fae9f0903c84f8f834ba8a492451f1c855bde083cca36527e4",
      "scenario/blender/prompt_jobs.py": "8fc6c9b949806c086e8595a0aa6221bb217cc3d3b32c92a7e7eb9cabc4714313",
      "scenario/blender/model_picker.py": "d5e9a5ddd15899aac0d0e35b03754687430bc80e3e85a77ffb0cfbe2620a2fb0",
      "scenario/mcp/tools_scenario.py": "1d613605107ee7db59790faec37e8a3bd4ee8a014c38b00e0b44be20b67f12c3",
      "tests/blender/test_credentials.py": "3878d0df15efe4b0bb2aec40b06aa1bd6118e4fb7146b3c011b16cfee32e306a",
      "tests/blender/test_reference_uploads.py": "5dd9f7f67bee68491cb098d3561a5595b7e446b6074826362b37695605176a60",
      "tests/unit/test_sdk_adapter.py": "f9df4ef657e0c4ab76e72bfe80ede1ea8bf0a0b9c3026579332603035a1bc7f5"
    }
  }
}
---

Evidence for [the canonical document](../../PRIVACY.md).
