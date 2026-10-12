---
{
  "type": "Evidence",
  "id": "docs-world-application.panorama-environment-lane",
  "title": "Environment lane results and World approval",
  "description": "Panorama generation leaves results saved for explicit World approval.",
  "evidence": {
    "path": "docs/WORLD_APPLICATION.md",
    "scope": "panorama-environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that native and MCP Environment lane jobs stop at saved results without automatic image import or World replacement, that their projection results reach the existing World approval unchanged, that the World confirmation does not state the projection while native saved-job rows label server-declared 360 results and MCP job_status reports projection, and that the guide still lists storage policy, undo, seam and pole quality, desktop evidence and live generation as open. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover a native panorama job left unapplied, then applied only to a newly selected scene after approval with the first scene's World unchanged, and the restart label. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): World candidates are #394's world_assets, which exclude material maps; the Environment label and Make HDRI never list a material map (installed test).",
    "sources": {
      "docs/WORLD_APPLICATION.md": "c8ae4e202ccb3a73a5c9e0637acc9f77944199d4e6fff8044871d48677019f07",
      "scenario/mcp/tools_scenario.py": "b4c064d45fda6d1ea734115574830ef887b6c09cfbc448973b14b275e7069a26",
      "scenario/blender/model_jobs.py": "4eeac905c9f752274d21fcd732d10fde0ffbba950d9c3ec90227ce5a39860f78",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/core/ui/saved_job_actions.py": "ab85bf3e0c7dd17305d7d199daeb17dd6c8d81f7aedae5619cf42cd40a7f1d9f",
      "tests/blender/test_model_generation.py": "f56f96f6b0727ca9f24c4104d0ed0ed0ab69034007f0febaf88439b365bd71ba",
      "tests/blender/test_panorama_lane.py": "e1371f77d663b68ee782cf6e636ff8b66e32a80a19fb0bfad48931545203f8e8"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/WORLD_APPLICATION.md#validation-and-remaining-integration).
