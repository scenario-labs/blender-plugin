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
    "limits": "Reviewed that every Film tool description states Film is experimental, that estimate_cost/generate name audio2txt and video23d as experimental with results kept in saved jobs, file-type-only import through prepare_result_application and motion/transcription handling not accepted (#190), and that list_models returns the picker's status text in each entry's capability_status (empty otherwise), named apart from the server's model status. Offline unit contracts tie the descriptions and the list_models capability_status field to the shared helper and reject a bare status key; an installed native test checks list_models capability_status values (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). The generated reference renders first lines only and is unchanged. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established. On 2026-10-10 the generic-import wording was rechecked for saved model package import: ModelJobs.actions offers import_model for importable GLB, glTF, FBX, OBJ and mesh PLY units, and the estimate_cost/generate descriptions and their unit contract now say a returned model or media file. Other claims and the review date are unchanged.",
    "sources": {
      "scenario/core/ui/capability_status.py": "5e18990d7117e420c6046cd01d992fa9dfe7f3dbb09702860ff5a45fc973dcd1",
      "scenario/mcp/tools_scenario.py": "fecde250ae186fbbc35bc55ff610c75a32457c0bef14e14de6a80499dd26ab70",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/unit/test_capability_status.py": "9b193ceca20c160ba7d49ba8bc5fa7310d08274ecebe52c3fc74f205567d9e53",
      "tests/unit/test_mcp_descriptions.py": "60c946c9982ed106fe57ac3dae623baa515d44f195c4d57b2a8240d60c1ad0c9",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tests/blender/test_mcp_tools.py": "79b4ca5ad4047a03e2128120d616f2bd5b2b8931083ea72cd32f7c3b13a26d99"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
