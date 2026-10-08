---
{
  "type": "Evidence",
  "id": "docs-mcp.asset-library-commands",
  "title": "Scoped asset library list and search commands",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "asset-library-commands",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Reviewed published SDK 2.2.0 assets.list and search.asset_search contracts, bounded raw-response pagination, adapter scope and online guards, worker ownership and native MCP projection. Synthetic tests exercise method/body/query mapping, malformed pages, cursors, errors, scene/project changes and omission of signed-URL/account/indexed-content fields. No live library call, generation, upload, file download or organization write was performed. Native Library presentation, integrated reference attachment, collection/tag editing and full release acceptance remain open. Search totals and pages are not a stable snapshot.",
    "sources": {
      "docs/MCP.md": "6490bb91e2a65d4fb88196b02bfad88a66a8fa00f84788f4de4dd6219cb0c8f8",
      "scenario/core/api/sdk_adapter.py": "1247ca79813ac35fe4bedad564e3588c41a52506e16580bb85178161ce875bfb",
      "scenario/core/jobs/coordinator.py": "1afa33eba542cef2a2b88802a7546226df58dd4e0515299a36e507ce3bd41d98",
      "scenario/core/jobs/workers.py": "716c07192e4fede52e5dcb696591d4183fd382bff34a72b695a51cddd41410a2",
      "scenario/blender/job_session.py": "9a899ad7818cb94814f46d819cb3ae512641129ea8e1e0ce67281a937733bc99",
      "scenario/mcp/tools_scenario.py": "c1671483ba62adb4e8c363184f117b1f008a33db2615c0cfbfd499ede69ad54c",
      "scenario/mcp/protocol.py": "796b929e5858ad287274d3bebf41fc25318ee5862a3df284111e117605b4a4c6",
      "tests/unit/test_scenario_sdk_contract.py": "4faea43c76c75a970259932757097c695fc26d073ff68b041f9eeeaa282c68b3",
      "tests/unit/test_asset_library.py": "37a3c81d3622d60c09760df4128b862e708f8234d748f0d5db44c9d7327669e1",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tests/unit/test_mcp_descriptions.py": "3a31a4562c3ea31c7e2e5f0ff52124ed852252344a923cc53d58b428b87c18c1",
      "tests/blender/test_asset_library.py": "0ca458607e9dc8bd11a7209ff300bd62dd209191a85278e5975a3bdc44cd33b8",
      "tests/blender/test_mcp_contracts.py": "c2beddc9165eb4cd6d408b3b75c96d1eca9aa3a1f52f05da51c52f5a720445f2",
      "tests/blender/run_all.py": "dfbf560cf66522ee3a8855caf0765750a094187c00be5bdafc09dc5a0cbd403e",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d"
    }
  }
}
---

Evidence for [the canonical guide](../../MCP.md).
