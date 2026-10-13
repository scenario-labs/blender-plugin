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
    "limits": "Reviewed that every Film tool description states Film is experimental, that estimate_cost/generate name audio2txt and video23d as experimental with results kept in saved jobs, file-type-only import through prepare_result_application and motion/transcription handling not accepted (#190), and that list_models returns the picker's status text in each entry's capability_status (empty otherwise), named apart from the server's model status. Offline unit contracts tie the descriptions and the list_models capability_status field to the shared helper and reject a bare status key; an installed native test checks list_models capability_status values (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). The generated reference renders first lines only and is unchanged. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established. On 2026-10-10 the generic-import wording was rechecked for saved model package import: ModelJobs.actions offers import_model for importable GLB, glTF, FBX, OBJ and mesh PLY units, and the estimate_cost/generate descriptions and their unit contract now say a returned model or media file. Other claims and the review date are unchanged. On 2026-10-10 the test_mcp_descriptions.py fingerprint was refreshed after a splat option parity test was added; the experimental status assertions are unchanged, and the review date is unchanged. Scoped re-inspection on 2026-10-13 for the #440 wording follow-up, not a full re-review. list_models still returns the picker's status text in capability_status; that text now reads Experimental: speech-to-text in testing or Experimental: video-to-motion in testing, from capability_status.label, because not accepted read as a refusal although these models run. test_mcp_tools asserts the new value and test_capability_status also rejects refusal wording. The tool descriptions describe the field, not its text, and are unchanged, as is the generated reference (gen_mcp_docs --check passes). The full installed suite passed 2,005 tests with 3 Windows-only skips on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. The fingerprints of capability_status.py, test_capability_status.py and test_mcp_tools.py are refreshed; the review date and base revision are unchanged. Review follow-up on 2026-10-13: the experimental line now reads Experimental: LoRAs and compositions in testing, so the picker's compositions are named too; refreshed fingerprints this topic had already re-checked.",
    "sources": {
      "scenario/core/ui/capability_status.py": "92ad5dfa68621fbaba58cbf0421c77f38640e7ebb276c5db8fc42928279bccc1",
      "scenario/mcp/tools_scenario.py": "fecde250ae186fbbc35bc55ff610c75a32457c0bef14e14de6a80499dd26ab70",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/unit/test_capability_status.py": "39f3733bbb2f9c6cfd02ec48ce7cd34debc17eb13281a3db0c71cd160719d7ec",
      "tests/unit/test_mcp_descriptions.py": "16f9e558e9abc040e080dd0ba1157ac57bd8a534a0f710247f5e8e5d007d0c02",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tests/blender/test_mcp_tools.py": "629bbebac74a14c121f3483cd584c1ac0ed27392cbfbc1d265bdb20c1b62f56e"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
