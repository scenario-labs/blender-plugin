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
    "limits": "Reviewed that build_request applies panorama_contract.prepare after the form body with the scene mode, model choice and GPT size preset, uses placeholders for waiting uploads and treats captures as non-panoramas, that saved panorama references are rechecked against the selected store with the shared saved_panorama_refs used by MCP and checked files carry their measured size, that the upload is bound to the checked bytes' SHA-256 and attaching other saved uploads to a panorama input is refused, that the panorama lane is never admitted to automatic image application, that poll projects meta panoramas and panorama_inputs from saved results on every view including restarted ones, and that Make HDRI checks the context token and saved result before switching the form and retiring its price, without quoting or submitting; the descriptors add the 360 label and a prefill group without a ModelJobs action. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover native and MCP body parity, single submission, uncertain submission, credential retirement, restart labels, Make HDRI and the byte-bound upload. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "6048a16622ea26525fe740fdda43740827e8af03d3a1d4fd60d30279670b4270",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b85199b13c0f7fdac0108efc28b39d7e35b0d7fe0b4ac60a39c95020c8d28521",
      "scenario/blender/generation.py": "265c53ce191b2b8d9f0eabecc1f0a726aa5758b0fae958ff1cae9b9aa0d620dd",
      "scenario/blender/panorama_lane.py": "84988f58d11e07b55f00285bcedae5d665324af4d195af9c50342193f4ff6e3b",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/blender/model_jobs.py": "b5174cdf8a73fea86b633fb660a7d942b0fd0f2516e81ec7477e1be6bb956b6b",
      "scenario/core/ui/saved_job_actions.py": "923ec72acee64754b948547f69d3b7f0b851c5c8d58a3156dc028e2131fa4756",
      "scenario/mcp/tools_scenario.py": "ddd3efd7b48378cec9c3bca01928ce1858cdabcf1d05bdbee086ed0b1d327b14",
      "tests/blender/test_panorama_lane.py": "539c48697cad7224d20b2638e6f92d63a83352b52190394f8c6842c7825f5e86",
      "tests/unit/test_panorama_contract.py": "03b45364309d8d1f2c5016966ed794f8f215088e6ed42047b0fdaf62cf53be70",
      "tests/unit/test_saved_job_actions.py": "ba376c38aeb9175d967e8447cf3e9a3dcf99d64e54b2fa651fdef782f5681621"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/BLENDER_JOB_CONTEXT.md#environment-lane-delivery).
