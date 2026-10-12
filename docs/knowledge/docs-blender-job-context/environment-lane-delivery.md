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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that build_request applies panorama_contract.prepare after the form body with the scene mode, model choice and GPT size preset, uses placeholders for waiting uploads and treats captures as non-panoramas, that saved panorama references are rechecked against the selected store with the shared saved_panorama_refs used by MCP and checked files carry their measured size, that the upload is bound to the checked bytes' SHA-256 and attaching other saved uploads to a panorama input is refused, that the panorama lane is never admitted to automatic image application, that poll projects meta panoramas and panorama_inputs from saved results on every view including restarted ones, and that Make HDRI checks the context token and saved result before switching the form and retiring its price, without quoting or submitting; the descriptors add the 360 label and a prefill group without a ModelJobs action. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover native and MCP body parity, single submission, uncertain submission, credential retirement, restart labels, Make HDRI and the byte-bound upload. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Gate re-review: Make HDRI and Reload call select_panorama_mode, which relists the HDRI or job mode's models even when the scene already shows that mode, because the model list is shared by scenes; an installed test covers Make HDRI after another scene listed its Generate mode. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): the Environment descriptors sit beside main's native use_first_frame control; the 360 label and Make HDRI read meta panoramas and panorama_inputs, which ModelJobs projects next to #394's world_assets, and an installed test checks that a package's material maps and a texture set's map reach none of them, and that the saved-panorama attachment and MCP refuse each of them with the saved-panorama message; on_model_changed stores contract values without RNA updates and re-arms the price for each value written.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "658d05900aad73739a2bd60cee1189bdc21abaae2067f2a4d110e69fab4070f1",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b06289a5193a4345b0dcdfe66a26df8cb362ec856918360deaadedee42d1ff84",
      "scenario/blender/generation.py": "50ad17c4f7bff740bdc8095261835fb3a89ee10cd6c45f16affa3895f09327d2",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/reference_form.py": "36cb61e5fb31c9efb01b6f7b36b0ff988c08e41bf9ea3985c9d0ef12e9c9cd50",
      "scenario/blender/model_jobs.py": "4eeac905c9f752274d21fcd732d10fde0ffbba950d9c3ec90227ce5a39860f78",
      "scenario/core/ui/saved_job_actions.py": "54c0728285999c86ba5bb43eb57229ad97b755b66a2ab30441c2f168d59c0e93",
      "scenario/mcp/tools_scenario.py": "b4c064d45fda6d1ea734115574830ef887b6c09cfbc448973b14b275e7069a26",
      "tests/blender/test_panorama_lane.py": "e1371f77d663b68ee782cf6e636ff8b66e32a80a19fb0bfad48931545203f8e8",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/unit/test_saved_job_actions.py": "5691a0d860e984d74dab8e4160bcf4cf3942f95899fc690a8f5cc2f3dde36402",
      "scenario/blender/operators.py": "b4f7e1f2974b1ca848c3d0e50594658b9708e328a3aaa4132f37fd41484179a0"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/BLENDER_JOB_CONTEXT.md#environment-lane-delivery).
