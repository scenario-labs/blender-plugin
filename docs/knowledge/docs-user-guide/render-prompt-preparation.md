---
{
  "type": "Evidence",
  "id": "docs-user-guide.render-prompt-preparation",
  "title": "Render look preparation with separate approval",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "render-prompt-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Reviewed render look preparation using the shared public SDK Prompt Spark command and existing explicit approval. Uploaded scene still/first-frame and ordered style images are bound at quote, approval and delivery; video assets never enter Spark images. Pending/wrong-scope references and uncertain submissions fail without automatic paid retry. Exact ZIP 77a45b82c4f569c66da4866a69fb3a2b898b736087e859de41544cfb3b7cf57f passed 564 native tests each on Blender 5.0.1, 5.1.2 and 5.2.1, macOS arm64. A 5.1.2 synthetic desktop run verified zero submissions before separate approval, one prompt submission, original-field delivery, keyboard edit, focus and viewport selection/zoom, clean exit and unchanged normal profile. The test-only Blender app identifier/signature differed; extension ZIP was unchanged. Initial fixture-origin invalidation and computer-control focus limitations are retained. No live service calls, final paid render, automatic video scene-still capture, other-lane result application or release acceptance is established; #263 remains unresolved. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: first_frame_enabled also counts a role-tagged first-frame slot that holds an asset without a local file (a saved-image handoff); uploaded slots, removal, changed-path and ordering rules are unchanged. The claims above still hold; the review date and base revision are unchanged. Re-checked 2026-10-10 after the first-frame routing change: the first frame stays image 1 of the request, so render_prompt.video_prompt still names @image1 (or Reference image 1) as the first-frame look and later images as styles; test_render_lanes asserts both for the captured Seedance 2.0 schema.",
    "sources": {
      "scenario/blender/render_prompt_jobs.py": "5789166b017b45e9a56e5390ccc8ce7b9d374e03932c080dee1a189ff08a5edd",
      "scenario/blender/prompt_jobs.py": "8fc6c9b949806c086e8595a0aa6221bb217cc3d3b32c92a7e7eb9cabc4714313",
      "scenario/blender/generation.py": "930df54b905404c84db8ccb05f0b707fc63eb7f9b367cc1ef179d67ba60c2c45",
      "scenario/blender/render_lanes.py": "f87937f114903d23fb5f5165aecfb3c4f32362b180e7999be6be2e8721ba85f2",
      "scenario/blender/render_references.py": "4897d8fe89d4bfbd9e171392cfa88feff4fa6a35ba88c40e4f63158fdb93aa47",
      "scenario/blender/reference_form.py": "9652fb1aa2644be3fb81bb59ba4d8034f0ea979ae50462701f607daf8d4b420d",
      "scenario/blender/props.py": "b0dab0b3ed3be39a7be1369c460592029294998526d13f38675c94b7c0e39713",
      "scenario/core/scene/render_prompt.py": "0217389b33a086f58ac9c8f5d5c9d39ce7c0484ee4d4de75964cb4e4d77b8c13",
      "scenario/core/api/sdk_adapter.py": "6cc3758eebf05f066a0aa11ed4d5c6ec96fb87b72f02f3d609cfdd97b88b044e",
      "tests/blender/test_prompt_tools.py": "db5604d54e01f6e4b45ea28f3f835c1ac91d87b0afab5bc9a634f635b802f883",
      "tests/blender/test_render_lanes.py": "55912a054a79518e980d06711f094dfadc9709370ba3090d010b74f0f46c74b5",
      "tests/blender/test_model_generation.py": "2e41a94ee2ec97c75f5a9969ff8c1aa044a7bfd9b866f57e432aa310658c368a",
      "docs/images/render-spark-price.png": "4af47f8c5f9b23395bae5d81ecfa1e70b9ab10f67005e995a2f38d2221d057cf",
      "docs/images/render-spark-result.png": "d620723e53088f95871db258873de228c5fc7024bff53dd721e070edb67328b2"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
