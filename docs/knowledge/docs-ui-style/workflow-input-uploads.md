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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed workflow input upload controls, kind-matched sources, confirmation text, preflight refusals, saved marker semantics, guarded pump attachment, saved-upload dialogs and clearing. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, clearing, drawing without mutation, selected-mesh quote provenance and MCP upload_reference to estimate_workflow; the full installed suite passed on Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 for one PR-head ZIP. No live service calls, uploads or spending occurred. Physical Studio interaction (file browser and confirmation from the popup, captures, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/UI_STYLE.md": "37ad8d256695b58623f85773c35bcafc66be622dddc5eb89f9b70864b358ef55",
      "scenario/blender/workflow_uploads.py": "eda175a406a3f8a41545096a0187607babe25e2c35317bb0e32c20d8615cf297",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "a8128de8e5522ea6483a5dc5be4e072155ba0be8f699bf4d8b396fa65c49f316",
      "scenario/blender/reference_form.py": "ace8e600949363221ddaabf34e8da11adf8b93b9b87b8cb0a81dc0fc67443f2f",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "715d054d96387ee6a50498f27a27b582f88aa3a93feb93a371f2205f84e7e42a",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080"
    }
  }
}
---

Evidence for [the canonical guide](../../UI_STYLE.md).
