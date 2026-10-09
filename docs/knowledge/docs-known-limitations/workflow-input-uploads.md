---
{
  "type": "Evidence",
  "id": "docs-known-limitations.workflow-input-uploads",
  "title": "Workflow input kinds that cannot be uploaded from Blender",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the uploadable kind set (image, audio, video, 3D) and the refusal of other declared kinds and listed allowed asset IDs. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow; the full installed suite passed on Blender 5.0.1, 5.1.2 and 5.2.1 macOS arm64 for one review follow-up ZIP. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Physical Studio interaction (file browser and confirmation from the popup, captures, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "aba5b70ab4543083fc55d8d418699249da2fd976ab5eeb3f3a358438ccf2d022",
      "scenario/blender/workflow_uploads.py": "bcc8b081aa5c8fdc8307e7f047004017371e56c00d01beacd0afddcd4f481b79",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "620e8cca89463f962dbce00da2787be236d805dedcd32b4e953e82775506d412",
      "scenario/blender/reference_form.py": "ace8e600949363221ddaabf34e8da11adf8b93b9b87b8cb0a81dc0fc67443f2f",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "247f750bfacbed87c65ad16824e81ad18ff67f8586ff12e7a774fe973784579e",
      "tests/blender/run_all.py": "d96251f4b93e6e052dad0bf6f0a88cc409f40c959e2162b2126000c5e0611080",
      "scenario/core/schema/forms.py": "bc1e91677c33f2a0f9ff0a8ce7be51ba238653aab52d9d88e3e37fd23ab962b4"
    }
  }
}
---

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
