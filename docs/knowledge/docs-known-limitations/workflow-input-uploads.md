---
{
  "type": "Evidence",
  "id": "docs-known-limitations.workflow-input-uploads",
  "title": "Workflow input kinds that cannot be uploaded from Blender",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the uploadable kind set (image, audio, video, 3D), the refusal of other declared kinds and listed allowed asset IDs, and that an upload still sending stops for good after a scene edit, frame change or undo because JobSession refuses its next admission, and that workflow and generation-form uploads share the facade's 128 handles, which finished uploads keep until runtime.retire_jobs replaces the facade after a credential or project change or a blend file load (job_session._load_pre deactivates the session and the next sync_catalog_context retires it) or runtime.shutdown resets it on unregister. A headless Blender 5.1.2 check confirmed that Open, Revert and File > New all run load_pre handlers. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, an object move and a frame change after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, a stopped-upload note that survives an unrelated undo and redo, notes on 16 other inputs and a retry refused before admission, stays off a same-named input of another loaded workflow, and that the next admitted upload into the input retires, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, a blend file load (the load_pre handler) after which the next use builds an empty upload facade without the earlier finished handles or stopped-upload notes, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. The full installed suite passed on Blender 5.1.2 macOS arm64 with this change; an earlier ZIP passed it on Blender 5.0.1 and 5.2.1 macOS arm64 before the rebase onto base_revision and before this change, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Uploads still stop for good after a scene edit, frame change or undo before they finish sending (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "0ad50428d27d68a3c297f8de4a1557fb7670cc2edcd23c0dc4b9a5f1a8e30bf2",
      "scenario/blender/workflow_uploads.py": "6d7b5f83e6bd3856414fcab8bce194d9c6adc561406e06e69bc89073b7bba18e",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "eb8c11578fd6255dee5c20297d74afadbbb5da7b95ecf046d221b45a8d9602e8",
      "scenario/blender/reference_form.py": "4e5f608933e27ff406009681d923ce2e03ad4ffa16b7d1ec70f486f74e12e2ee",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "b3dd35338334a6363c1da52ee02df9aa6f55ecc06747aed05c184c9c91a5accc",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/core/schema/forms.py": "bc1e91677c33f2a0f9ff0a8ce7be51ba238653aab52d9d88e3e37fd23ab962b4",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "scenario/blender/runtime.py": "fb83ceaa622cbbfbea25210d2bb8d480231510d11712f58df34f45f41c13cf59"
    }
  }
}
---

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
