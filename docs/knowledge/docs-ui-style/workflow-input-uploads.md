---
{
  "type": "Evidence",
  "id": "docs-ui-style.workflow-input-uploads",
  "title": "Explicit uploads into loaded workflow file inputs",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed workflow input upload controls, kind-matched sources, confirmation text, preflight refusals, saved marker semantics including the operator undo step and history-retired origins, automatic release of an upload stopped before sending with a drawn note, release on Cancel preparation, the Stop waiting control and its confirmation, connection rechecks, guarded pump attachment, saved-upload dialogs and clearing. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, an object move and a frame change after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. The full installed suite passed on Blender 5.1.2 macOS arm64 with this change; an earlier ZIP passed it on Blender 5.0.1 and 5.2.1 macOS arm64 before the rebase onto base_revision and before this change, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Uploads still stop for good after a scene edit, frame change or undo before they finish sending (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/UI_STYLE.md": "683708959e0eb5e477fcb90cc9c6ad9b02670f29dbbd9cb1e1988c94f5ce9d99",
      "scenario/blender/workflow_uploads.py": "2ccb7239d41a1f3aaef0adcc967692ebc04d923d402c917111e62df1ad1d667f",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "7b460f4c88225765e2c252f9cba182112bddfa257411e69596063a19cbf17f8b",
      "scenario/blender/reference_form.py": "964f0e6b626414ad184b9a96cb7993921cb4a3ec0a1d9ba5953d6a4351bc7301",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "d1583249ee7c99f4869c3cdc5f3b90d90332d0b54b8cdafbbd2a649789668d89",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8"
    }
  }
}
---

Evidence for [the canonical guide](../../UI_STYLE.md).
