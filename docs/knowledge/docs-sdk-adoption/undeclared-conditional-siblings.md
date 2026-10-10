---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.undeclared-conditional-siblings",
  "title": "Conditional rules naming undeclared inputs",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "undeclared-conditional-siblings",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed strict form preparation, parse_schema required flags, SDK estimate preparation, the native panel schema cache and local MCP model_schema and body validation for conditional rules that name an input the schema does not declare. Offline unit tests and installed native tests with synthetic transport cover ifDefined, ifNotDefined, declared and undeclared names together, nested inputs, blank names and the captured Seedance 2.0 Mini record. One free live dry run priced Seedance 2.0 Mini through prepare_run and SDKAdapter.estimate_model in the key's default scope; nothing was submitted. The interpretation assumes the omitted input has no default. Falsy ifNotDefined values, ifNotDefined rules naming several inputs and required.conditional rules are not reconciled with the service here. Native suite passed on macOS arm64 Blender 5.1.2 only. No human approval is implied.",
    "sources": {
      "scenario/core/schema/forms.py": "b5402f205ae67d0b29d7d5904223be80c40a397f6b89c5345171f1f6f44df6b3",
      "scenario/core/schema/params.py": "6325b4ecd1f9962f034eb60684a0ced786d2136855840bc4d26472a31cbc85a8",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/blender/generation.py": "6f73c4ba35ceb97097d1356b2267c5b2b7a2a7105b6900d0376d2604f9e9de8f",
      "scenario/mcp/tools_scenario.py": "8613fe347b43421261f0462fe3972e777fffb6f35f17f9cd4a26d8b321d25331",
      "tests/unit/test_model_payload_validation.py": "09e3c89522f1e6b936f78f4c6b11cfbec77c35a1f7958707e1867bec0670a973",
      "tests/blender/test_model_payload_validation.py": "b7e0d5e8af6ac6ff4f24f68d4c1f4e40995e018be1136b06b3cd131d789c4145",
      "tests/blender/test_mcp_tools.py": "dfaf3ff28044fe86f6caca238258372a7107acd0e21309e7feccd95ded82623f",
      "tests/fixtures/models/model_bytedance-seedance-2-0-mini.json": "452ebb7169a55855fd495c94947724bfd09221014fb8f929726216744fec032e"
    }
  }
}
---

# Conditional rules naming undeclared inputs

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
