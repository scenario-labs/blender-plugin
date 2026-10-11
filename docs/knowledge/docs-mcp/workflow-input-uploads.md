---
{
  "type": "Evidence",
  "id": "docs-mcp.workflow-input-uploads",
  "title": "MCP parity for workflow input uploads",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that local MCP keeps upload_reference/capture_reference and estimate_workflow without protocol changes, that their descriptions and upload note name workflow parameters, that the parity statement excludes the native Render result snapshot, which has no capture_reference source, and that generated tool tables are unchanged. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, an object move and a frame change after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, an upload paused in another scene that Upload again then abandoned (delivery ends with an error, the marker and values stay, no part is sent and Stop waiting frees the input), a stopped-upload note that survives an unrelated undo and redo, notes on 16 other inputs and a retry refused before admission, stays off a same-named input of another loaded workflow, and that the next admitted upload into the input retires, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, a blend file load (the load_pre handler) after which the next use builds an empty upload facade without the earlier finished handles or stopped-upload notes, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. After the rebase onto base_revision, the full installed suite on Blender 5.1.2 macOS arm64 ran 1335 tests with one failure, the saved remote-job action labels in test_result_actions, which fails identically on base_revision itself; every workflow upload test passed, and the abandoned-upload test failed when ABANDONED was removed from the finished delivery states. Earlier ZIPs passed the suite on Blender 5.0.1 and 5.2.1 macOS arm64 before this rebase, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Uploads still stop for good after a scene edit, frame change or undo before they finish sending (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/MCP.md": "3e6466809b0bc3aa86b1590f43390735d45f72356d6ac3c6a87cdd9579dbeaaa",
      "scenario/blender/workflow_uploads.py": "b4c391e0b8f1b932acacc29dda46cd24b8d076654aaede61dee8ff400bc2dde0",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "53f03716813f4a3480fa808a820f6269de566b5c1710448e2f56c3e12702fad3",
      "scenario/blender/reference_form.py": "eeeeb2b6d5b59c3ff0777b0632cb3d604318467224dc6783e7c8ee7c23710a9a",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "e44eed64a97fe600de33cb121b2ec3a0ccf7813789a3a53a2f9a09d40e5a5c74",
      "tests/blender/run_all.py": "e39d59b3ca315e0ed927da91ec4b6b8653790d6352c18fb003df510979c43724",
      "scenario/mcp/tools_scenario.py": "4520137c47b688075d33558b36f9ed4a34cf73eb22d3f9b2e28e26199dc9af78",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e"
    }
  }
}
---

Evidence for [the canonical guide](../../MCP.md).
