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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the #190 limitation that models offering video23d or audio2txt show a visible experimental status in the picker, the Model row and list_models. Generation works and results stay in saved jobs. ModelJobs.actions and prepare_result_application offer generic import by file type, so a returned GLB or media file may import, but speech-to-text and video-to-motion handling is not accepted (#190). Unit and installed native tests cover the status text, its presence/absence and the MCP field (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). Video-to-motion and speech-to-text input and result handling remain the open capability request in #190. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established.",
    "sources": {
      "scenario/core/ui/capability_status.py": "2fd4bae1adc9c9d96ecdc6f165635fa91487a0154f48d028729f5c07550d05b8",
      "scenario/blender/model_picker.py": "c949fbdf60dd4f5c7c911e806e3335e7502dd63086d5a1d40d54231c9dd5f1bc",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/mcp/tools_scenario.py": "b1226d92dd5b5aba2be56a4e3079d437ec93a865b63ba5a911d1338962115d42",
      "tests/unit/test_capability_status.py": "54a9ad8b7cf5a1d184bcde5d391f0ed704ba466c088f96cdd0179ee8ae213827",
      "tests/unit/test_mcp_descriptions.py": "b568866568aa4d33840106780e3483494217deb0e5c1cc95a271f94d7fbf9b35",
      "tests/blender/test_model_picker.py": "a9650ac1310cc8d4d044815b4e63aa35d1574a9acf421bafeb76b77e6f8b69fe",
      "tests/blender/test_mcp_tools.py": "7495191ed808d9d8eed1943218300f733a5de6872529f2a80db3fc63e48ddb00"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
