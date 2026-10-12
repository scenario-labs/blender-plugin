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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that MCP Environment lane jobs stop at saved results without automatic image import or World replacement, that their projection results reach the existing World approval unchanged, and that the guide no longer lists SDK model validation and estimates among missing work while still listing the native tab, storage policy, undo, seam and pole quality and live generation. Installed native tests on macOS arm64 Blender 5.1.2 check that a saved panorama job leaves the scene World and images unchanged. No live panorama output, World application of a generated panorama, other Blender version or desktop interaction is established.",
    "sources": {
      "docs/WORLD_APPLICATION.md": "007b9f4b31a312261d2038a85486ad851aacf5797c693eaa55e1d600b90b90d6",
      "scenario/mcp/tools_scenario.py": "54dd2fc57b96ddcac1f8e44fa97df513487a7f3537266797a2f5ab024a760ca0",
      "scenario/blender/model_jobs.py": "88f17955538534d792b7408cf8e11e705bb2e6ee82d584173d51a365504c467d",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "tests/blender/test_model_generation.py": "402e14442c01ec69eec18d401b3aebbc32ce7d080efc69e2ee32e9ea837a039c"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/WORLD_APPLICATION.md#validation-and-remaining-integration).
