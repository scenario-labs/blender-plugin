---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.capture-upload-origin",
  "title": "docs/SDK_UPLOADS.md: scene captures keep their upload origin",
  "description": "Viewport/camera still and clip captures send no deferred same-frame update that would invalidate their own upload origin.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "capture-upload-origin",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed still/clip capture restoration of the preview-range toggle, the clip span under an enabled preview range, reference and render-form upload origin capture after the snapshot, and the unchanged conservative frame hook. Blender 5.1.2 sources show that the toggle, preview bounds, current frame and subframe send a frame notifier, while frame range, resolution and camera writes do not. Native background regressions record capture writes to those properties and replay the frame hook Blender runs in the GUI through the real upload path; background mode cannot process notifiers itself. An isolated macOS arm64 Blender 5.1.2 GUI run of exact ZIP f05d9058155397f48df2148f25ced2d4596e9b8b55515808b78e253bc78a3265, driven through the local MCP with free catalog reads, prepared Render Image still and Render Video clip scene references with the preview range off and on: no deferred frame hook followed either capture, upload origins stayed current and staging reached the upload request, which a test guard refused. The unfixed main ZIP reproduced the origin error in the same runs. Frame writes, frame_set and a same-value toggle write after an origin still invalidated it. No upload transfer, live provider, other OS or Blender version GUI run, physical input, or explicit clip span differing from an enabled preview range in an origin-capturing path is established. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/capture.py": "6179fd2b14824b172e2e19a3d7c730bfddf620ae5b5cef51bb874453a8b657e1",
      "scenario/blender/reference_uploads.py": "00aec147e040a08dd1e79deb7a4cece57fcf6e21fff277b11f25ba62acabf607",
      "scenario/blender/reference_form.py": "520583bf3399a0f79a880f027a5beb61de9dd0eea83c89f9d7500c17b80b4d13",
      "scenario/blender/render_references.py": "ca13ca03952d4bdfe13c8280e46f192fb5e7e525778393cdba2c9d71ae37db71",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "tests/blender/test_capture.py": "f54c5c336fedb667c3ff74538e96cea4ceda8ccdc223296a39cab16e48344240",
      "tests/blender/test_reference_uploads.py": "b32d4113bc38854373c7267ba5cbb4cb37736a0363fac14a71ccdaa70be5919a",
      "tests/blender/helpers.py": "eb9b1148a436a61479cea0e8f69a02bd18eda96b8c265066ccd3d1ab5ec97ff7",
      "tests/blender/test_job_session.py": "4bd4561da96485dcbce97d89c5063fe800bfc86f7e6a97bee339bcb93744d399"
    }
  }
}
---

# Scene captures keep their upload origin

Evidence for [the canonical document](../../SDK_UPLOADS.md).
