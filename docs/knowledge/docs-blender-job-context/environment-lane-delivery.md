---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.environment-lane-delivery",
  "title": "Environment lane request, references and saved results",
  "description": "Shared contract preparation, panorama reference checks and saved-result projection.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "environment-lane-delivery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that build_request applies panorama_contract.prepare after the form body with the scene mode, model choice and GPT size preset, uses placeholders for waiting uploads and treats captures as non-panoramas, that saved panorama references are rechecked against the selected store with the shared saved_panorama_refs used by MCP and checked files carry their measured size, that the upload is bound to the checked bytes' SHA-256 and attaching other saved uploads to a panorama input is refused, that the panorama lane is never admitted to automatic image application, that poll projects meta panoramas and panorama_inputs from saved results on every view including restarted ones, and that Make HDRI checks the context token and saved result before switching the form and retiring its price, without quoting or submitting; the descriptors add the 360 label and a prefill group without a ModelJobs action. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover native and MCP body parity, single submission, uncertain submission, credential retirement, restart labels, Make HDRI and the byte-bound upload. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Gate re-review: Make HDRI and Reload call select_panorama_mode, which relists the HDRI or job mode's models even when the scene already shows that mode, because the model list is shared by scenes; an installed test covers Make HDRI after another scene listed its Generate mode.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "6048a16622ea26525fe740fdda43740827e8af03d3a1d4fd60d30279670b4270",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "d6c25753c641a863e99920e980ec4e14ead175b5f44c8d7725b7f454c51f3a52",
      "scenario/blender/generation.py": "7fd6bfde60cb2d5ffa758d85fe55ee2c0c582864991e88d2dd79e4d150c24c0b",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/blender/model_jobs.py": "b5174cdf8a73fea86b633fb660a7d942b0fd0f2516e81ec7477e1be6bb956b6b",
      "scenario/core/ui/saved_job_actions.py": "923ec72acee64754b948547f69d3b7f0b851c5c8d58a3156dc028e2131fa4756",
      "scenario/mcp/tools_scenario.py": "ddd3efd7b48378cec9c3bca01928ce1858cdabcf1d05bdbee086ed0b1d327b14",
      "tests/blender/test_panorama_lane.py": "a556e269ab2ea9817ac51c92177d03e79b1cac826ee941cc88b4a61a99ce3172",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/unit/test_saved_job_actions.py": "ba376c38aeb9175d967e8447cf3e9a3dcf99d64e54b2fa651fdef782f5681621",
      "scenario/blender/operators.py": "d0139c445429e43ed86bd233ddcfa4a850c142c6ecbb90835ec048bfa051d7a6"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/BLENDER_JOB_CONTEXT.md#environment-lane-delivery).
