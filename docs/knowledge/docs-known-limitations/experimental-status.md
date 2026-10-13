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
    "limits": "Reviewed the #190 limitation that models offering video23d or audio2txt show a visible experimental status in the picker, the Model row and list_models (capability_status); the viewport composer's model chip does not show it. They can be submitted; provider behavior and result handling are not accepted. ModelJobs.actions and prepare_result_application offer generic import by file type, so a returned model (GLB, glTF, FBX, OBJ or mesh PLY) or media file may import, but speech-to-text and video-to-motion handling is not accepted (#190). Unit and installed native tests cover the status text, its presence/absence and the MCP capability_status field (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). Video-to-motion and speech-to-text input and result handling remain the open capability request in #190. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established. On 2026-10-10 the generic-import wording was rechecked for saved model package import: ModelJobs.actions offers import_model for importable GLB, glTF, FBX, OBJ and mesh PLY units, and the estimate_cost/generate descriptions and their unit contract now say a returned model or media file. Other claims and the review date are unchanged. On 2026-10-10 the test_mcp_descriptions.py fingerprint was refreshed after a splat option parity test was added; the experimental status assertions are unchanged, and the review date is unchanged. Scoped re-inspection on 2026-10-13 for the #440 wording follow-up, not a full re-review. The limitation's text is unchanged; the status it names now reads Experimental: speech-to-text in testing or Experimental: video-to-motion in testing, from capability_status.label, because not accepted read as a refusal although these models run. The picker and the Model row still draw it read-only from model_picker (the whole current file was read for these claims; its trained-picker additions since the recorded fingerprint draw no capability status), and list_models still returns the same text in capability_status: test_model_picker and test_mcp_tools assert the new text, and test_capability_status also rejects refusal wording. The full installed suite passed 2,005 tests with 3 Windows-only skips on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. The fingerprints of capability_status.py, test_capability_status.py, model_picker.py, test_model_picker.py and test_mcp_tools.py are refreshed; the review date and base revision are unchanged. Review follow-up on 2026-10-13: the experimental line now reads Experimental: LoRAs and compositions in testing, so the picker's compositions are named too; refreshed fingerprints this topic had already re-checked.",
    "sources": {
      "scenario/core/ui/capability_status.py": "92ad5dfa68621fbaba58cbf0421c77f38640e7ebb276c5db8fc42928279bccc1",
      "scenario/blender/model_picker.py": "d6aab6af577510662a6fd0219bc0cfdf130766669194f44fb97d95b00a96035e",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/mcp/tools_scenario.py": "fecde250ae186fbbc35bc55ff610c75a32457c0bef14e14de6a80499dd26ab70",
      "tests/unit/test_capability_status.py": "39f3733bbb2f9c6cfd02ec48ce7cd34debc17eb13281a3db0c71cd160719d7ec",
      "tests/unit/test_mcp_descriptions.py": "16f9e558e9abc040e080dd0ba1157ac57bd8a534a0f710247f5e8e5d007d0c02",
      "tests/blender/test_model_picker.py": "87ea96a14d69a87957bf34e3bd8fec3dbf239eb4cb11c44a5ef90df7f8a6535a",
      "tests/blender/test_mcp_tools.py": "629bbebac74a14c121f3483cd584c1ac0ed27392cbfbc1d265bdb20c1b62f56e",
      "scenario/blender/composer/draw.py": "db9ce841a722d8b7761786bd1ea44c6a1d7e189ce0673560d5e604f35a78c0cf"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
