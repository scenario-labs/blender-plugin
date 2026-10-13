---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.workflow-input-uploads",
  "title": "Retained Studio attach-file behavior for workflow inputs",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that the retained Studio local-file attachment for workflow inputs is implemented through the shared upload session and Library-equivalent binding, without copying Studio runtime code. Installed-ZIP native tests with synthetic SDK/storage transports cover confirmation, preflight refusals including missing and unreadable files, connection and scope rechecks before start, marker removal after a staging failure that sent nothing while uncertain initialization keeps it, a revoked origin after local staging on an array that already holds a value (marker released, value kept, no service request, a drawn note, a later upload appended), a chosen file that still attaches through frame changes, an unrelated object move and render-thread updates, Cancel preparation freeing a waiting, undo-restored or retired-connection marker, Stop waiting after an upload stopped mid-transfer, an upload paused in another scene that Upload again then abandoned (delivery ends with an error, the marker and values stay, no part is sent and Stop waiting frees the input), a stopped-upload note that survives an unrelated undo and redo, notes on 16 other inputs and a retry refused before admission, stays off a same-named input of another loaded workflow, and that the next admitted upload into the input retires, the operator result when a failed start keeps the marker, marker-gated pricing, guarded delivery, Library-equivalent scope/value binding, saved-upload confirmation after blend reopen and undo/redo, a blend file load (the load_pre handler) after which the next use builds an empty upload facade without the earlier finished handles or stopped-upload notes, undo around an upload, clearing, drawing without mutation or schema reparsing, a background Render result upload, selected-mesh quote provenance and MCP upload_reference to estimate_workflow. After the rebase onto base_revision, the full installed suite on Blender 5.1.2 macOS arm64 ran 1335 tests with one failure, the saved remote-job action labels in test_result_actions, which fails identically on base_revision itself; every workflow upload test passed, and the abandoned-upload test failed when ABANDONED was removed from the finished delivery states. Earlier ZIPs passed the suite on Blender 5.0.1 and 5.2.1 macOS arm64 before this rebase, which is not evidence for the current sources. The operator's own undo push was not driven through a native popup; tests record the equivalent undo step explicitly. No live service calls, uploads or spending occurred. Snapshot uploads still stop for good after a scene edit, frame change, render or undo before they finish sending, and chosen files after undo, redo, removal of their scene or a file load (the shared JobSession origin policy). A blend file saved before the staged record was first observed has no request link, so after reopening Cancel preparation cannot free its marker and Stop waiting is needed. Physical Studio interaction (file browser and confirmation from the popup, captures, Stop waiting, DPI and IME), other platforms and live upload/workflow acceptance remain under #66/#68; this does not close issue or release scope. On 2026-10-13 chosen-file uploads moved to destination-only origins (see the file-upload-destination topic): the origin statements above were corrected, the stopped-upload tests now stop a chosen file by revoking its origin with JobSession.invalidate_all, which Undo and Redo run first, and only the fingerprints of sources that changed solely for that work were refreshed; other claims and the review date are unchanged.",
    "sources": {
      "docs/STUDIO_ADOPTION.md": "0481fd48e3b2e9852f3fe9b63eff0e4ece57fe915cdde93e7fb5ffb147b3b563",
      "scenario/blender/workflow_uploads.py": "b4c391e0b8f1b932acacc29dda46cd24b8d076654aaede61dee8ff400bc2dde0",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_references.py": "b46d87799fb86f3fc9b673f35ac0913521aa6309f17166092fc9fbba20f24a70",
      "scenario/blender/reference_uploads.py": "108dfdbd475ff13a398f3a03ac203efeec203f80b2c888ab4f55a6cbae929142",
      "scenario/blender/reference_form.py": "eeeeb2b6d5b59c3ff0777b0632cb3d604318467224dc6783e7c8ee7c23710a9a",
      "scenario/blender/registry.py": "f059b1e767524f507458512dd222fa04fc9c7f6d7d4448403bf95d8df5624ab9",
      "tests/blender/test_workflow_uploads.py": "e44eed64a97fe600de33cb121b2ec3a0ccf7813789a3a53a2f9a09d40e5a5c74",
      "tests/blender/run_all.py": "e39d59b3ca315e0ed927da91ec4b6b8653790d6352c18fb003df510979c43724"
    }
  }
}
---

Evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
