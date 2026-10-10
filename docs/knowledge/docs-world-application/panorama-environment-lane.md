---
{
  "type": "Evidence",
  "id": "docs-world-application.panorama-environment-lane",
  "title": "Environment lane results and World approval",
  "description": "Panorama generation through MCP leaves results saved for explicit World approval.",
  "evidence": {
    "path": "docs/WORLD_APPLICATION.md",
    "scope": "panorama-environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that MCP Environment lane jobs stop at saved results without automatic image import or World replacement, that their projection results reach the existing World approval unchanged, and that the guide no longer lists SDK model validation and estimates among missing work while still listing the native tab, storage policy, undo, seam and pole quality and live generation. Installed native tests on macOS arm64 Blender 5.1.2 check that a saved panorama job leaves the scene World and images unchanged. No live panorama output, World application of a generated panorama, other Blender version or desktop interaction is established.",
    "sources": {
      "docs/WORLD_APPLICATION.md": "d26bd7ddfcb3ddbf1ec4e2581652c609bd3dafde7c764420b71c82acd9e9e840",
      "scenario/mcp/tools_scenario.py": "77dbdf62a8929019548650c80682cb41c1436a466591244b412ff03c0405ba34",
      "scenario/blender/model_jobs.py": "56e8699e97278dcd39bdf38404e9dc2407f22217053a98f663d11e8a4e6c284c",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "tests/blender/test_model_generation.py": "a4d32c045b2764d55af10ca7128ceb0dbca48c23a88eeab5cc234b0c8b310d75"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/WORLD_APPLICATION.md#validation-and-remaining-integration).
