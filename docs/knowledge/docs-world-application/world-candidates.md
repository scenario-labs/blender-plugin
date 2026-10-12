---
{
  "type": "Evidence",
  "id": "docs-world-application.world-candidates",
  "title": "Saved World candidates and numbering",
  "description": "Which saved results the World action offers and how its buttons are numbered.",
  "evidence": {
    "path": "docs/WORLD_APPLICATION.md",
    "scope": "world-candidates",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected World candidate selection. ModelJobs.actions, the projected world_assets list and prepare_world_application share panorama.world_candidate, which keeps PNG, JPEG and OpenEXR media types and excludes saved results whose metadata declares a texture role. The shared saved_job_actions.describe descriptors, drawn by job_recovery.draw_controls, offer Set panorama as World (N) only for a projected world_assets entry whose media type is also in the World result types job_recovery passes, and number it by its position among all results, as the model import buttons (such as Import GLB model (N)) and the strip actions do; a view without world_assets offers no World button. Headless native tests reproduce a 3D package (GLB, PBR maps and one unmapped image) and a texture set, including refused MCP World preparation for a map; unit tests cover the predicate and the descriptor numbering and candidate filter. A free read of a live 3D package on 2026-10-10 showed its four PNG maps declaring texture roles at 2048x2048. The saved job records no image dimensions, so an ordinary image without a role is still offered and fails during application; a dimension-based offer needs saved dimensions. No desktop interaction review of the changed buttons, other OS, paid generation, #98 completion or release acceptance. On 2026-10-12 the job_recovery.py, saved_job_actions.py and test_saved_job_actions.py fingerprints were refreshed after import_model descriptors became one control per importable model unit, labelled by format and still numbered by saved-asset index; World candidate selection, its descriptor filter and numbering are unchanged. The UI style and World application guides and the installed World candidate test now name that control Import GLB model (1); the statement above names it the same way, and the other statements and the review date are unchanged.",
    "sources": {
      "scenario/core/scene/panorama.py": "3680feac102599bf04bf5b0e6a7a63f0d292c9536f9833848ba5217c8619a890",
      "scenario/core/jobs/result_metadata.py": "775986522c43e4b837f3deb333f964ca721eb6b8c74bd0282f40824a19c4af17",
      "scenario/blender/model_jobs.py": "24b608edabf19ad9c8176e08ebc3db51ac5ad9acbb960f1bba39368a5f1c5dec",
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/mcp/tools_scenario.py": "2bbfed621f202d313835f3115d800c56cfe4c34614560af7003391059862cabf",
      "tests/unit/test_panorama.py": "0b2006c19f9ce2edf276579d77745011664edaebfe4dc2d962b7b2dc1b03188a",
      "tests/blender/test_model_generation.py": "8d02d88a009cb1924c61171d12d08c378cab562dfaaaa6ff55cbc0ad60697ce2",
      "scenario/core/ui/saved_job_actions.py": "d0afb3cb400c639d28822029f0650dad9fad52784e67bd75ea19ffc8bf043972",
      "tests/unit/test_saved_job_actions.py": "ce4563039276adabf07edcd4d6465b4e3a31d5c33b165e527bf8ae22532c0c10",
      "tests/blender/test_result_actions.py": "9ec19d46012acacd7d8fa88ff0b07548978b1ab13f61b0346c26c8b31e677805"
    }
  }
}
---

# Saved World candidates and numbering

Evidence for [the canonical document](../../WORLD_APPLICATION.md).
