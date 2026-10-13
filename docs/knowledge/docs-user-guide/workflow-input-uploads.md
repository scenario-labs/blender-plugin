---
{
  "type": "Evidence",
  "id": "docs-user-guide.workflow-input-uploads",
  "title": "Uploading files and snapshots into workflow inputs",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "workflow-input-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed against the shortened guide, which keeps four claims for this topic and links SDK_UPLOADS.md#workflow-input-attachment for every other case: file inputs accept an upload (step 3 of Run a workflow); uploads into workflow inputs work like form references; editing the scene, changing the frame or rendering stops a snapshot that is still sending, and it cannot resume; an upload that does not attach is resolved with Inspect uploads, Stop waiting or Clear reference. Checked against workflow_uploads.py (review and preflight refusals, confirmation, start, delivery, nothing-sent notes, Stop waiting, drawing), workflow_controls.py (the marker blocks pricing; the per-input draw and Clear reference button), workflow_references.py (Clear reference empties and unticks the input, removes the marker and request link and leaves the upload in saved uploads), reference_form.py (shared sources, Inspect uploads actions, Cancel preparation only for a prepared record, single-use saved-upload attachment), reference_uploads.py (snapshot and chosen-file origins, sent_nothing, release after cancellation), job_session.py and core/jobs/origins.py (scene, frame and render-thread handlers revoke snapshot origins; a chosen file keeps a destination-only origin until undo, redo, scene removal or a file load), runtime.py and registry.py. Corrections proposed for the guide: only image, audio, video and 3D inputs without listed allowed asset IDs take an upload; workflow uploads use Upload file or a snapshot button and ask for confirmation, unlike form references; Inspect uploads cancels only an upload that never started sending. The linked section covers the delegated cases in maintainer terms, except Clear reference on an input that is still marked, and it implies rather than states the fresh price after attachment. Unit tests run: tests/unit/test_forms.py and tests/unit/test_job_origins.py, 48 passed. Installed native tests in test_workflow_uploads.py and test_reference_uploads.py were read, not run; the file-upload-destination topic records a full installed-suite pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 on 2026-10-13 whose fingerprints for workflow_uploads.py, reference_uploads.py, reference_form.py, job_session.py, origins.py and both test files match the bytes reviewed here. Tests simulate render-thread callbacks; a real render, timeline playback, the file browser, confirmation popups, Inspect uploads and Stop waiting clicked on a desktop, DPI, IME and other platforms remain unverified. The paid desktop pass in the release acceptance guide (local image file, viewport and camera captures into workflow inputs at UI scale 1.0) ran on an earlier build; audio, video and 3D uploads and UI scale 2.0 remain under #66/#68. No live service calls, uploads or spending occurred in this review, and it does not close issue or release scope. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "a9e84d847e233ba08cacc75cc0fcbc8c0c7eae455e2862ff8584fe447d0bf90b",
      "scenario/blender/workflow_uploads.py": "70e6543b1546ce6ec67e48b07ab7b5605e86be349e19abb6aa0e9de5da778151",
      "scenario/blender/workflow_controls.py": "8b515b7c19fb0c6b4bc797a612a6158dac0bbecffb2a8254d259cb1a4ae956fd",
      "scenario/blender/workflow_references.py": "64eb574c5c8c377dcfbe91c91f0dab27ffcbb52445f68628c460aa0274ff5535",
      "scenario/blender/reference_uploads.py": "108dfdbd475ff13a398f3a03ac203efeec203f80b2c888ab4f55a6cbae929142",
      "scenario/blender/reference_form.py": "3b7433c9e3a9243f08a9fa031cf7bafddcdaa03ff5f2663455aa209f30ef5138",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "tests/blender/test_workflow_uploads.py": "dd47d5900ae5c69e4380e56b96e66b00a93366a60566920789034c4a3bc575a8",
      "tests/blender/run_all.py": "bcce33605252d54bbc0e78e45f0806809c9ec1b515b0c0fe0e97f0a4372b0944",
      "scenario/blender/job_session.py": "b20ae0be8fbec16510d6750fa50757f7830ebf937f65649e186c16ee9068fb28",
      "scenario/blender/runtime.py": "c8303eead552a5de421c69c56cb754c2d463f117909b46273c791d46275eb707",
      "scenario/core/jobs/origins.py": "28e971a6b14f4f340b35bf38ee5d496da1574120dfc34e7eae2b9d7511e1e74e",
      "tests/blender/test_reference_uploads.py": "567e65da79edb8878fa09163962e1363ffe754ada8a070ba0e12d8858fdf735b",
      "tests/unit/test_job_origins.py": "1065f4125092c4171d4e680bce2cb48641f5335a1a4d4b6589ba704cf9779be6",
      "docs/SDK_UPLOADS.md": "634b44c756406302aa9f7ae9fbc4862d43f5e20e45c8b604340e2e848577f75f"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
