---
{
  "type": "Evidence",
  "id": "docs-mcp.experimental-status",
  "title": "Explicit experimental status for Film and unaccepted capabilities",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "experimental-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that every Film tool description states Film is experimental, that estimate_cost/generate name audio2txt and video23d as experimental with results kept in saved jobs, file-type-only import through prepare_result_application and motion/transcription handling not accepted (#190), and that list_models returns the picker's status text in each entry's status (empty otherwise). Offline unit contracts tie the descriptions and the list_models status field to the shared helper; an installed native test checks list_models status values (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). The generated reference renders first lines only and is unchanged. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established.",
    "sources": {
      "scenario/core/ui/capability_status.py": "2fd4bae1adc9c9d96ecdc6f165635fa91487a0154f48d028729f5c07550d05b8",
      "scenario/mcp/tools_scenario.py": "b1226d92dd5b5aba2be56a4e3079d437ec93a865b63ba5a911d1338962115d42",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/unit/test_capability_status.py": "54a9ad8b7cf5a1d184bcde5d391f0ed704ba466c088f96cdd0179ee8ae213827",
      "tests/unit/test_mcp_descriptions.py": "b568866568aa4d33840106780e3483494217deb0e5c1cc95a271f94d7fbf9b35",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tests/blender/test_mcp_tools.py": "7495191ed808d9d8eed1943218300f733a5de6872529f2a80db3fc63e48ddb00"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
