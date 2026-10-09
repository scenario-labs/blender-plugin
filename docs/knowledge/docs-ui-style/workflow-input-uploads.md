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
    "limits": "Reviewed workflow input upload controls, kind-matched sources, confirmation text, preflight refusals, saved marker semantics including the operator undo step and history-retired origins, automatic release of an upload stopped before sending with a drawn note that stays through undo and redo while the workflow and input values are unchanged and that the next admitted upload into the input retires, release on Cancel preparation, the Stop waiting control and its confirmation, connection rechecks, guarded pump attachment, saved-upload dialogs and clearing. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, an object move and a frame change after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, a stopped-upload note that survives an unrelated undo and redo, notes on 16 other inputs and a retry refused before admission, stays off a same-named input of another loaded workflow, and that the next admitted upload into the input retires, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. The full installed suite passed on Blender 5.1.2 macOS arm64 with this change; an earlier ZIP passed it on Blender 5.0.1 and 5.2.1 macOS arm64 before the rebase onto base_revision and before this change, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Uploads still stop for good after a scene edit, frame change or undo before they finish sending (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/UI_STYLE.md": "65bf4473dc797e4a6cf18b64532ca6b27d8734ad97a5b7401459d7ab1daa8a24",
      "scenario/blender/workflow_uploads.py": "6d7b5f83e6bd3856414fcab8bce194d9c6adc561406e06e69bc89073b7bba18e",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "eb8c11578fd6255dee5c20297d74afadbbb5da7b95ecf046d221b45a8d9602e8",
      "scenario/blender/reference_form.py": "4e5f608933e27ff406009681d923ce2e03ad4ffa16b7d1ec70f486f74e12e2ee",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "e9f8b3458ec13addc22550e482177c4f1c84e610e41545d8fc3fc42ace6a029e",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8"
    }
  }
}
---

Evidence for [the canonical guide](../../UI_STYLE.md).
