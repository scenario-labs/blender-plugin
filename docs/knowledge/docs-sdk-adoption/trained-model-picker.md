---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-picker",
  "title": "Trained models in the native picker",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the new section and the two sentences it changed in the catalog and route sections: the catalog load queuing JobManager.fetch_trained, which reads the private list again with SDKCatalog.fetch_list (SDKAdapter.models: models.with_raw_response.list, privacy=private, status=trained, project on every page) and pairs it through SDKCatalog.trained_models with the cached or in-flight public list; trained_catalog and trained_catalog_failed events checked against the current catalog, a failure kept apart from public lanes and retried only by the Trained chip or a refresh, and any unexpected worker failure reported as a generic failure with only its type logged; base descriptions through SDKCatalog.get (SDKAdapter.model: models.with_raw_response.retrieve, project in the query) only from the Trained chip of an open picker dialog (a trained list delivered after the dialog closed starts none), in lane order, at most 400 per lane and connection, batches of 10, one failure skipped and three in a row ending the scan with the sanitized reason, and a batch the main thread cannot apply ending its scan; trained_offers pairing records with detailed bases whose slot runs them and requiring strength bounds or a default for LoRAs; forms keeping IDs, kinds, strengths and a scope tag; trained_routes.apply rebuilding the payload on every request; strengths rounded to four decimals; and an installed test in which the form's payload and an MCP estimate_cost given the same parameters dry-run identical bytes. No SDK method, raw fallback, extension or dependency changed. Unit tests run the workers with scripted catalogs and the pure module with captured fixtures. The installed suite on macOS arm64 Blender 5.1.2 passed 1,233 tests (2 Windows-only skips), including the 18 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records. MCP trained listings and payload building from picks in the Image lane remain #97 work; render_form inspection lists the Render Image form's choice (docs-mcp.render-form-trained-models). No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "docs/SDK_ADOPTION.md": "8e246556373e27968786256e99574b2f27ffe8a03e9a8f39ec4a6fa8c83cc179",
      "scenario/core/jobs/manager.py": "3f63861575bde2e83b74ab3e8982215432b72615f9b00ba220bb3da3673c3080",
      "scenario/core/api/trained_offers.py": "3f26bf5fc4de7b66004722e90aa257e364b4d740637730fd9600682302cdf339",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/blender/trained_models.py": "b22065b710995723e43a954910245edc7033710a00dceee93e8000c15023b654",
      "scenario/blender/model_picker.py": "5125349af1e9d02202344ed4758824d50404c98397f702a7a7a8f30be2892bef",
      "scenario/blender/handlers.py": "0dccbbd97f2be476960f2709516989e6f218bd7372ef003c15138ddf6c737eb7",
      "scenario/blender/generation.py": "599f62901fc5a23dfcfd12afb862f983435651a52df2faf3e7f579310f05e122",
      "tests/unit/test_trained_catalog_workers.py": "97b5b63442914ed13d04c31834fd9996e68bd53a37eb9ae92ba0c69a8c9cada7",
      "tests/unit/test_trained_offers.py": "1165fd41f3398f8a229c8da20f2f39381aa1603bf4d2dd4b2255de43162e5df3",
      "tests/blender/test_trained_models.py": "cdc0dad13557080489a7b8957cf6dd2ab73f1dd534c90460650fa5d1b4458f9d",
      "tests/blender/test_offline_runtime.py": "daf592f19255d371263812862759c19b8cb7b7ce045505c090280c0d2898b18e",
      "tests/blender/test_sdk_estimates.py": "6161576ea0a9ccdf4c3b2844dc42e0777863c3e01effe7eebb3fc07dbb3e4725"
    }
  }
}
---

Evidence for [trained models in the native picker](../../SDK_ADOPTION.md#trained-models-in-the-native-picker).
