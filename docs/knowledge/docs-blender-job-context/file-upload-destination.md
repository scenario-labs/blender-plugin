---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.file-upload-destination",
  "title": "docs/BLENDER_JOB_CONTEXT.md: chosen-file uploads bind only to their destination",
  "description": "A file the user chose keeps uploading through scene edits, frame changes and renders; scene snapshots stay bound to the revision they showed.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "file-upload-destination",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "4dfca796e1a082d89e0a0af091e78e161fa77fca",
    "limits": "Reviewed that ReferenceUploads.start takes a destination-only origin (JobSession.capture_destination) only for an explicitly external file: local MCP upload_reference and the generation-form and workflow-input File sources. Viewport, camera and Render Result stills, clips, selected meshes and Film captures keep revision-bound origins. OriginRevisions keeps one destination token per scene; dependency and frame invalidation and the render-thread reset (reset(keep_destinations=True)) leave it, while scene removal (prune_missing_scenes), Undo/Redo, file loading and deactivation (reset) revoke it. Destination origins with a target, forged tokens and another registry's scenes are never current. Delivery and attachment still require the selected scene, the unchanged form slot or workflow input and the connection scope; JobCoordinator._prepare refuses a destination-only origin, so no paid request can bind one; a restart keeps the upload's binding kind. Installed-ZIP native tests with the synthetic SDK transport and part-upload stub cover MCP, generation-form and workflow-input file uploads that reach imported and attach through frame changes, an unrelated object move and render-thread handler calls, made before each command and while the signed part is in flight; camera still and clip captures that still stop before any request after each of those updates; a chosen file that stops after Undo or after its scene is removed, including at the worker-side guard; and a restart after Undo that takes a new destination-only origin. Unit tests cover the registry and the paid-path refusal. The full installed suite passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 (2002 tests each, 3 skipped). Render-thread callbacks were simulated by calling the registered handler from a worker thread; a real render, timeline playback in a GUI window, live S3 or Scenario uploads and physical interaction were not exercised.",
    "sources": {
      "scenario/core/jobs/origins.py": "28e971a6b14f4f340b35bf38ee5d496da1574120dfc34e7eae2b9d7511e1e74e",
      "scenario/core/jobs/coordinator.py": "e7d7384e68b53caf90ff206118be9b61da4e3e990f4604084f275176459a3652",
      "scenario/blender/job_session.py": "b20ae0be8fbec16510d6750fa50757f7830ebf937f65649e186c16ee9068fb28",
      "scenario/blender/reference_uploads.py": "108dfdbd475ff13a398f3a03ac203efeec203f80b2c888ab4f55a6cbae929142",
      "scenario/blender/reference_form.py": "3b7433c9e3a9243f08a9fa031cf7bafddcdaa03ff5f2663455aa209f30ef5138",
      "scenario/blender/workflow_uploads.py": "70e6543b1546ce6ec67e48b07ab7b5605e86be349e19abb6aa0e9de5da778151",
      "scenario/mcp/tools_scenario.py": "f9e4447cc3b1a1cae05f5fd3148940f25f39c3bbfbbc62b876ab524b5af0d83f",
      "tests/unit/test_job_origins.py": "1065f4125092c4171d4e680bce2cb48641f5335a1a4d4b6589ba704cf9779be6",
      "tests/blender/test_reference_uploads.py": "567e65da79edb8878fa09163962e1363ffe754ada8a070ba0e12d8858fdf735b",
      "tests/blender/test_reference_form.py": "96e9f097cb981141f1a4a1774adde0c09b880d699d20e68a556544a75f8bb21f",
      "tests/blender/test_workflow_uploads.py": "dd47d5900ae5c69e4380e56b96e66b00a93366a60566920789034c4a3bc575a8",
      "tests/blender/test_job_session.py": "098a513567a9ac9e846283075420900298d53a9595462b63af178957ef2955df"
    }
  }
}
---

# Chosen-file uploads bind only to their destination

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
