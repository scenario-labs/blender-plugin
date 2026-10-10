---
{
  "type": "Evidence",
  "id": "docs-mcp.saved-package-import",
  "title": "MCP saved model package import",
  "description": "Model approval fields, job_status import units and the model_import summary.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the model branch of prepare_result_application (format, primary, members with roles and media types, glTF resources, cursor and per-format note), prepare_asset_application routing, the prepare_result_application, apply_result_application and job_status descriptions, and ModelJobs.status import_units, import_findings and model_import. The generated table renders first lines and schemas, and the schema is unchanged; gen_mcp_docs --check passes. Installed MCP journeys cover an OBJ package with reuse, a changed member, a changed GLB, the FBX frame-rate mismatch and splat and STL refusal, and offline unit contracts check the descriptions. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). No headless MCP CLI run for a non-GLB package, live provider acceptance or splat import is claimed. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "ab08d69c3d107831c5d4e99a050594f10e431cc829c2f3077b22a08fa9668020",
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/blender/model_application.py": "c7fff225f53b796c0206ef4d3ba69ca4ff077d8cfdb3bc062dfbd4051ab3e0a3",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/unit/test_mcp_descriptions.py": "60c946c9982ed106fe57ac3dae623baa515d44f195c4d57b2a8240d60c1ad0c9",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3"
    }
  }
}
---

# MCP saved model package import

Evidence for [the canonical document](../../MCP.md#overview).
