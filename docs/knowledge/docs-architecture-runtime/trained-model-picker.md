---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.trained-model-picker",
  "title": "Trained-model catalog load and picker reads in the active SDK catalog",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed only the changed sentence: generation.request_catalog queues the private trained list read with the public catalog through trained_models.request, the picker's Trained chip starts base description reads on demand (trained_models.request_bases, and from a delivered list only while model_picker.trained_view_open), local MCP tools do not list trained models (render_form inspection reports only the Render Image form's chosen slots), and model_filter and catalog.models_for_lane keep LoRAs, compositions and other trained types out of the lane lists and the other chips while private custom models that reach them stay listed. Retirement clears the trained state with the catalog (generation.clear_catalog). Other claims of the paragraph keep their own topic. The installed suite on macOS arm64 Blender 5.1.2 passed 1,233 tests (2 Windows-only skips), including the 18 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records. No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "docs/architecture/runtime.md": "3139ff0f81c20ea1c7cb83d067a3cf633b3ff23b74fc8fd0cc6c56639dadadbe",
      "scenario/blender/generation.py": "599f62901fc5a23dfcfd12afb862f983435651a52df2faf3e7f579310f05e122",
      "scenario/blender/trained_models.py": "b22065b710995723e43a954910245edc7033710a00dceee93e8000c15023b654",
      "scenario/blender/model_picker.py": "5125349af1e9d02202344ed4758824d50404c98397f702a7a7a8f30be2892bef",
      "scenario/blender/runtime.py": "09baca93189f61922aad7199ed86d6c924cd1a8ae9de85759c8f030ac66e8c70",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/mcp/tools_scenario.py": "f75442a1f4f93f33bee636109813a1f070f27aa47b5d21013887cd9854bc8326",
      "tests/blender/test_offline_runtime.py": "daf592f19255d371263812862759c19b8cb7b7ce045505c090280c0d2898b18e",
      "tests/blender/test_trained_models.py": "cdc0dad13557080489a7b8957cf6dd2ab73f1dd534c90460650fa5d1b4458f9d"
    }
  }
}
---

Evidence for [the active SDK catalog](../../architecture/runtime.md#active-sdk-catalog).
