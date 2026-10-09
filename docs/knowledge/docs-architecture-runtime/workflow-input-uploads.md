---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.workflow-input-uploads",
  "title": "Workflow input uploads in the shared runtime",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed main-thread delivery through the application pump, the form signature marker extension that preserves unmarked signatures, shared Library binding, file and connection preflight, staging-failure marker removal, the operator undo step, history and retirement cleanup, coordinator mesh bindings and unchanged MCP protocol. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow; the full installed suite passed on Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 for one review follow-up ZIP before the rebase onto base_revision, and again on Blender 5.1.2 macOS arm64 only after it. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Open review finding: an object or frame change, or an undo that keeps the marker, before import invalidates the captured origin, so the next initialization, part or completion request is refused and the marker stays, including for a prepared upload that sent nothing. Such a halted prepared or uploading record cannot be refreshed or attached, and on an array input only Clear references releases the marker, which also empties the array. The documented recovery does not cover this case yet. Physical Studio interaction (file browser and confirmation from the popup, captures, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/architecture/runtime.md": "df6b72a8eccbc3a95099f8e441ed784d9245c000f9f6e249ecc7a36f100a12ef",
      "scenario/blender/workflow_uploads.py": "bcc8b081aa5c8fdc8307e7f047004017371e56c00d01beacd0afddcd4f481b79",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "620e8cca89463f962dbce00da2787be236d805dedcd32b4e953e82775506d412",
      "scenario/blender/reference_form.py": "ace8e600949363221ddaabf34e8da11adf8b93b9b87b8cb0a81dc0fc67443f2f",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "247f750bfacbed87c65ad16824e81ad18ff67f8586ff12e7a774fe973784579e",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/blender/runtime.py": "43003d6a75ea5b11f2459ba56d39db94d43359a1cd1564765a10471d7979889e",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d"
    }
  }
}
---

Evidence for [the canonical guide](../../architecture/runtime.md).
