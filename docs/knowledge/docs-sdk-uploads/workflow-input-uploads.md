---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.workflow-input-uploads",
  "title": "Workflow input attachment over the shared upload lifecycle",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed that workflow uploads reuse ReferenceUploads, the selected JobSession, scoped upload store, workers and the existing uploads.create/trigger_action/retrieve adapter mapping without a new SDK method, transport or retry path; marker, delivery, shared capacity and saved-attachment guards, the facade's 128 per-session handles that workflow uploads also take and keep until the facade is replaced (credential or project change) or the extension restarts, one stopped-upload note per input, stored by scene session UID and input name and shown while the input keeps its recorded values, which survives undo and redo and other inputs' notes until the next upload into the input, including the extended ReferenceUpload.sent_nothing policy (the upload commands save INITIALIZING before the create request and cancel only from PREPARED), the request link at first observation, release on cancellation, Stop waiting, file and connection preflight and undo-step semantics; quote-time captured mesh binding; and that MCP parity excludes the native Render result snapshot. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, an object move and a frame change after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, a stopped-upload note that survives an unrelated undo and redo and notes on 16 other inputs, and that the next upload into the input retires, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. The full installed suite passed on Blender 5.1.2 macOS arm64 with this change; an earlier ZIP passed it on Blender 5.0.1 and 5.2.1 macOS arm64 before the rebase onto base_revision and before this change, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Uploads still stop for good after a scene edit, frame change or undo before they finish sending (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/SDK_UPLOADS.md": "3f0147d032ca7f99753d78333f236c070460acbfb87b05d758152c9b44be5140",
      "scenario/blender/workflow_uploads.py": "e25e38afef2d7144b0793846477ac8cc65ca474399e97cb57d285336f78074f8",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "d4aa13347c0bb4524081406c37e347df97323fd720748740a81008b5eeb845f0",
      "scenario/blender/reference_form.py": "4e5f608933e27ff406009681d923ce2e03ad4ffa16b7d1ec70f486f74e12e2ee",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "b07443d9dcb969db0bc01e3538844fea1b7068ac8bbbed19203fda640b19f1a2",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/core/api/sdk_adapter.py": "1247ca79813ac35fe4bedad564e3588c41a52506e16580bb85178161ce875bfb",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8",
      "scenario/core/jobs/uploads.py": "0eb0df9afcde2f37fcdba510ada065b489d52be058ab7319362af56be4232bea",
      "scenario/core/jobs/upload_store.py": "3b8be69ce6abb8593e7eb28b56403574b6a95534d8c9adf46564bb4941cc502c"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_UPLOADS.md).
