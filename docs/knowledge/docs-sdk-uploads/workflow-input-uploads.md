---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.workflow-input-uploads",
  "title": "Workflow input attachment over the shared upload lifecycle",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that workflow uploads reuse ReferenceUploads, the selected JobSession, scoped upload store, workers and the existing uploads.create/trigger_action/retrieve adapter mapping without a new SDK method, transport or retry path; marker, delivery, shared capacity and saved-attachment guards, the facade's 128 per-session handles that workflow uploads also take and keep until runtime.retire_jobs replaces the facade (a credential or project change, or a blend file load: job_session._load_pre deactivates the session and the next sync_catalog_context retires it) or runtime.shutdown resets it on unregister, one stopped-upload note per input, stored by scene session UID and input name and shown only while the loaded workflow, schema and input values match those recorded, which survives undo and redo, other inputs' notes and a retry refused before admission until another upload is admitted into the input, a Library or saved-upload attachment or Clear reference sets its values, or the facade holding it is replaced, including the extended ReferenceUpload.sent_nothing policy (the upload commands save INITIALIZING before the create request and cancel only from PREPARED), the request link at first observation, release on cancellation, delivery that ends with an error and keeps the marker for a failed, canceled or abandoned record (Upload again abandons the original; its new upload is not bound to the input), Stop waiting, file and connection preflight and undo-step semantics; quote-time captured mesh binding; and that MCP parity excludes the native Render result snapshot. A headless Blender 5.1.2 check confirmed that Open, Revert and File > New all run load_pre handlers. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, an object move and a frame change after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, an upload paused in another scene that Upload again then abandoned (delivery ends with an error, the marker and values stay, no part is sent and Stop waiting frees the input), a stopped-upload note that survives an unrelated undo and redo, notes on 16 other inputs and a retry refused before admission, stays off a same-named input of another loaded workflow, and that the next admitted upload into the input retires it, as do a Library attachment followed by Clear reference and Clear reference alone, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, a blend file load (the load_pre handler) after which the next use builds an empty upload facade without the earlier finished handles or stopped-upload notes, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. On the current sources, the full installed suite on Blender 5.1.2 macOS arm64 ran 1336 tests with one failure, the saved remote-job action labels in test_result_actions, which fails identically on base_revision itself; every workflow upload test passed. The abandoned-upload test failed when ABANDONED was removed from the finished delivery states, and the attach-and-clear note test failed before attachment and Clear reference retired the note. Earlier ZIPs passed the suite on Blender 5.0.1 and 5.2.1 macOS arm64 before this rebase, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Uploads still stop for good after a scene edit, frame change or undo before they finish sending (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/SDK_UPLOADS.md": "655d414470c63a9fa0f1be8596b17ae75de88ee7b3b395f29d6b453642b6ccd0",
      "scenario/blender/workflow_uploads.py": "e86561520d47aaa3b1073c5f261903562d3f525dbf74cd7d90a72c2c8ff80c9b",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "64eb574c5c8c377dcfbe91c91f0dab27ffcbb52445f68628c460aa0274ff5535",
      "scenario/blender/reference_uploads.py": "53f03716813f4a3480fa808a820f6269de566b5c1710448e2f56c3e12702fad3",
      "scenario/blender/reference_form.py": "eeeeb2b6d5b59c3ff0777b0632cb3d604318467224dc6783e7c8ee7c23710a9a",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "44d4a738607c304cf43fe15b144373833cc41edfaa76f531803689f4ea06a14e",
      "tests/blender/run_all.py": "e39d59b3ca315e0ed927da91ec4b6b8653790d6352c18fb003df510979c43724",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "scenario/core/jobs/coordinator.py": "86d723261acb1fda7ef9718248be03c46de52cf6086277f15b673a46487551f5",
      "scenario/blender/job_session.py": "2d429d766cc70c9eb20d61400241e92b1dfeab46949c7d9d6392e36b33599f82",
      "scenario/core/jobs/uploads.py": "06cacc568478204ddbbba7f67f03d48da85fe492a8db8dcf04df14db35944aef",
      "scenario/core/jobs/upload_store.py": "0e8f7a2799779200e666b76699948cd4c00db734fb71a92a26d9181154785f7a",
      "scenario/blender/runtime.py": "64b6e702f91c80be66ee6378125745b2db1d10f583bddd9f449dd3a06d15b4f8"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_UPLOADS.md).
