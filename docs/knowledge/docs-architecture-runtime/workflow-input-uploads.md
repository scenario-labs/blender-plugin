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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed main-thread delivery through the application pump, the form signature marker extension that preserves unmarked signatures, shared Library binding, history and retirement cleanup, coordinator mesh bindings and unchanged MCP protocol. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, clearing, drawing without mutation, selected-mesh quote provenance and MCP upload_reference to estimate_workflow; the full installed suite passed on Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 for one PR-head ZIP. No live service calls, uploads or spending occurred. Physical Studio interaction (file browser and confirmation from the popup, captures, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/architecture/runtime.md": "070095241d00ef47f38b168edfd7c80dd8095335f024e433f830ffd9ed5ee07c",
      "scenario/blender/workflow_uploads.py": "eda175a406a3f8a41545096a0187607babe25e2c35317bb0e32c20d8615cf297",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "a8128de8e5522ea6483a5dc5be4e072155ba0be8f699bf4d8b396fa65c49f316",
      "scenario/blender/reference_form.py": "ace8e600949363221ddaabf34e8da11adf8b93b9b87b8cb0a81dc0fc67443f2f",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "715d054d96387ee6a50498f27a27b582f88aa3a93feb93a371f2205f84e7e42a",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d"
    }
  }
}
---

Evidence for [the canonical guide](../../architecture/runtime.md).
