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
    "limits": "Reviewed that native and MCP Environment lane jobs stop at saved results without automatic image import or World replacement, that their projection results reach the existing World approval unchanged, that the World confirmation does not state the projection while native saved-job rows label server-declared 360 results and MCP job_status reports projection, and that the guide still lists storage policy, undo, seam and pole quality, desktop evidence and live generation as open. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover a native panorama job left unapplied, then applied only to a newly selected scene after approval with the first scene's World unchanged, and the restart label. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/WORLD_APPLICATION.md": "641180189f11d77793f6a7ca2c35b15a999c7a6b87c4699bc3220c7e24085cfd",
      "scenario/mcp/tools_scenario.py": "ddd3efd7b48378cec9c3bca01928ce1858cdabcf1d05bdbee086ed0b1d327b14",
      "scenario/blender/model_jobs.py": "b5174cdf8a73fea86b633fb660a7d942b0fd0f2516e81ec7477e1be6bb956b6b",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/core/ui/saved_job_actions.py": "923ec72acee64754b948547f69d3b7f0b851c5c8d58a3156dc028e2131fa4756",
      "tests/blender/test_model_generation.py": "7a259312ca4bdbbcf45f14b34985cb71bcd722da2d8546439d4a206704a05049",
      "tests/blender/test_panorama_lane.py": "539c48697cad7224d20b2638e6f92d63a83352b52190394f8c6842c7825f5e86"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/WORLD_APPLICATION.md#validation-and-remaining-integration).
