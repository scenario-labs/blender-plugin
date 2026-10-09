---
{
  "type": "Evidence",
  "id": "docs-mcp.workflow-input-uploads",
  "title": "MCP parity for workflow input uploads",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that local MCP keeps upload_reference/capture_reference and estimate_workflow without protocol changes, that their descriptions and upload note name workflow parameters, and that generated tool tables are unchanged. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow; the full installed suite passed on Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 for one review follow-up ZIP. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Physical Studio interaction (file browser and confirmation from the popup, captures, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/MCP.md": "e853250b9fa0005e1ab6a075f5967d4f7fc39941996f30c6b618ecdf35fc70c8",
      "scenario/blender/workflow_uploads.py": "bcc8b081aa5c8fdc8307e7f047004017371e56c00d01beacd0afddcd4f481b79",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "620e8cca89463f962dbce00da2787be236d805dedcd32b4e953e82775506d412",
      "scenario/blender/reference_form.py": "ace8e600949363221ddaabf34e8da11adf8b93b9b87b8cb0a81dc0fc67443f2f",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "247f750bfacbed87c65ad16824e81ad18ff67f8586ff12e7a774fe973784579e",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/mcp/tools_scenario.py": "2d0a0303e2d56c88fda0a79f31a8bc9c7886add5d3c253a9764bf17ef48a3ed8",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e"
    }
  }
}
---

Evidence for [the canonical guide](../../MCP.md).
