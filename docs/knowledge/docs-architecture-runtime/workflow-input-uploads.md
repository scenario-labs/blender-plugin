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
    "limits": "Reviewed main-thread delivery through the application pump, the form signature marker extension that preserves unmarked signatures, shared Library binding, file and connection preflight, JobSession refusal of the next upload admission after origin invalidation, the extended ReferenceUpload.sent_nothing policy (failed staging, an admission refused while prepared, cancellation) and the resulting marker removal, the request link at first observation, release on cancellation through the marker-to-ticket ledger or that request link, Stop waiting, the operator undo step including a failed start that keeps the marker, history and retirement cleanup (bindings are discarded while stopped-upload notes, one per input stored by scene session UID and input name with the loaded workflow and schema, stay), coordinator mesh bindings and unchanged MCP protocol. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, an object move and a frame change after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, a stopped-upload note that survives an unrelated undo and redo, notes on 16 other inputs and a retry refused before admission, stays off a same-named input of another loaded workflow, and that the next admitted upload into the input retires, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. The full installed suite passed on Blender 5.1.2 macOS arm64 with this change; an earlier ZIP passed it on Blender 5.0.1 and 5.2.1 macOS arm64 before the rebase onto base_revision and before this change, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Uploads still stop for good after a scene edit, frame change or undo before they finish sending (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/architecture/runtime.md": "150bafbbb4a1449de5cb4faa9b1ecd0351d5d7d9b1add62c9070f1f7186e84cd",
      "scenario/blender/workflow_uploads.py": "6d7b5f83e6bd3856414fcab8bce194d9c6adc561406e06e69bc89073b7bba18e",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "eb8c11578fd6255dee5c20297d74afadbbb5da7b95ecf046d221b45a8d9602e8",
      "scenario/blender/reference_form.py": "4e5f608933e27ff406009681d923ce2e03ad4ffa16b7d1ec70f486f74e12e2ee",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "e9f8b3458ec13addc22550e482177c4f1c84e610e41545d8fc3fc42ace6a029e",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/blender/runtime.py": "43003d6a75ea5b11f2459ba56d39db94d43359a1cd1564765a10471d7979889e",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8",
      "scenario/core/jobs/uploads.py": "0eb0df9afcde2f37fcdba510ada065b489d52be058ab7319362af56be4232bea",
      "scenario/core/jobs/upload_store.py": "3b8be69ce6abb8593e7eb28b56403574b6a95534d8c9adf46564bb4941cc502c"
    }
  }
}
---

Evidence for [the canonical guide](../../architecture/runtime.md).
