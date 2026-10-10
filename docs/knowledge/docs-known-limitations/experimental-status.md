---
{
  "type": "Evidence",
  "id": "docs-known-limitations.experimental-status",
  "title": "Explicit experimental status for Film and unaccepted capabilities",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "experimental-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the #190 limitation that models offering video23d or audio2txt show a visible experimental status in the picker, the Model row and list_models (capability_status); the viewport composer's model chip does not show it. They can be submitted; provider behavior and result handling are not accepted. ModelJobs.actions and prepare_result_application offer generic import by file type, so a returned model (GLB, glTF, FBX, OBJ or mesh PLY) or media file may import, but speech-to-text and video-to-motion handling is not accepted (#190). Unit and installed native tests cover the status text, its presence/absence and the MCP capability_status field (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). Video-to-motion and speech-to-text input and result handling remain the open capability request in #190. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established. On 2026-10-10 the generic-import wording was rechecked for saved model package import: ModelJobs.actions offers import_model for importable GLB, glTF, FBX, OBJ and mesh PLY units, and the estimate_cost/generate descriptions and their unit contract now say a returned model or media file. Other claims and the review date are unchanged.",
    "sources": {
      "scenario/core/ui/capability_status.py": "5e18990d7117e420c6046cd01d992fa9dfe7f3dbb09702860ff5a45fc973dcd1",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/mcp/tools_scenario.py": "fecde250ae186fbbc35bc55ff610c75a32457c0bef14e14de6a80499dd26ab70",
      "tests/unit/test_capability_status.py": "9b193ceca20c160ba7d49ba8bc5fa7310d08274ecebe52c3fc74f205567d9e53",
      "tests/unit/test_mcp_descriptions.py": "60c946c9982ed106fe57ac3dae623baa515d44f195c4d57b2a8240d60c1ad0c9",
      "tests/blender/test_model_picker.py": "2db431d736b07a17576cdf167b464f677042f5e7b9b3b87bb7f5ee73b514b2ca",
      "tests/blender/test_mcp_tools.py": "79b4ca5ad4047a03e2128120d616f2bd5b2b8931083ea72cd32f7c3b13a26d99",
      "scenario/blender/composer/draw.py": "db9ce841a722d8b7761786bd1ea44c6a1d7e189ce0673560d5e604f35a78c0cf"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
