---
{
  "type": "Evidence",
  "id": "docs-user-guide.workflow-input-uploads",
  "title": "Uploading files and snapshots into workflow inputs",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the user-facing upload steps, sources, single/array rules, pricing block, file checks, staging-failure retry, undo behavior, saved-upload recovery and clearing against the implementation. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow; the full installed suite passed on Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 for one review follow-up ZIP before the rebase onto base_revision, and again on Blender 5.1.2 macOS arm64 only after it. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Open review finding: an object or frame change, or an undo that keeps the marker, before import invalidates the captured origin, so the next initialization, part or completion request is refused and the marker stays, including for a prepared upload that sent nothing. Such a halted prepared or uploading record cannot be refreshed or attached, and on an array input only Clear references releases the marker, which also empties the array. The documented recovery does not cover this case yet. Physical Studio interaction (file browser and confirmation from the popup, captures, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/USER_GUIDE.md": "25194a6d2ca132f6d5709a6e5ccb3afa451d09b79cb4dad9afb5511ddd55c39e",
      "scenario/blender/workflow_uploads.py": "bcc8b081aa5c8fdc8307e7f047004017371e56c00d01beacd0afddcd4f481b79",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "620e8cca89463f962dbce00da2787be236d805dedcd32b4e953e82775506d412",
      "scenario/blender/reference_form.py": "ace8e600949363221ddaabf34e8da11adf8b93b9b87b8cb0a81dc0fc67443f2f",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "247f750bfacbed87c65ad16824e81ad18ff67f8586ff12e7a774fe973784579e",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
