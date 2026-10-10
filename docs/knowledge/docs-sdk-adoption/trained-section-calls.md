---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-section-calls",
  "title": "Scenario calls of trained strengths and project defaults",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-section-calls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the paragraph added to the native-picker section and the status sentence of the routes section: strength fields, project defaults and the composer label add no Scenario operation, SDK method, raw fallback, extension or dependency; strengths are bounded by the cached base description; a project default is checked with trained_routes.apply against cached descriptions and the trained list before it changes a form; trained_defaults._base_waiting starts at most one existing description read through generation.request_model (JobManager.fetch_models, SDKCatalog.get, SDKAdapter.model, models.with_raw_response.retrieve with the selected project) when online, not while one is pending and not after a recorded failure; the quote check reads every chosen model again unchanged; defaults stay in the local job store. Local MCP listings and MCP defaults remain #97 work. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,249 tests (OK, 2 Windows-only skips) with ZIP sha256 269ada4c3673990da2c8735dd8b15f8341c0ad69ed5ef0dc8559d77882a6d8c7, whose 148 Python files match git archive of the reviewed feature commit, including the 16 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "scenario/blender/trained_defaults.py": "de64246c52dc3107a6892ac9ed0e2a892b4d2a4bcbbd0d3f831f23ec09636648",
      "scenario/blender/trained_section.py": "e4498d61dc304586bcfb4f6b8e487fecb9b18572fcc08587f38560637a4615b5",
      "scenario/blender/trained_models.py": "2c4dadd4a0a5ef2216ca00045b43724da50b5fe5bd1c0bcaddf1a471a3642bd9",
      "scenario/blender/generation.py": "38115244a8350c53148761f57ba0e12ea40ebba64db7e9879f1767dcf444d934",
      "scenario/blender/render_commands.py": "9551e08bb7a898fc9b0872c98a0a5e699ed9c50bede5e8a6e0c69f8cf273f4de",
      "scenario/core/jobs/manager.py": "3f63861575bde2e83b74ab3e8982215432b72615f9b00ba220bb3da3673c3080",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/core/api/trained_routes.py": "908b49b8b5ecdd8ee5869fe07178b80b9e2d3a385b11d694babaf2515a3f0162",
      "tests/blender/test_trained_section.py": "06de61b3c34d0281161432c8f9b637ada8838c760a3b72d977ff9cfe17e18cbf"
    }
  }
}
---

Evidence for [trained models in the native picker](../../SDK_ADOPTION.md#trained-models-in-the-native-picker).
