---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-picker",
  "title": "Trained models in the native picker",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed the new section and the two sentences it changed in the catalog and route sections: the catalog load queuing JobManager.fetch_trained, which reads the private list again with SDKCatalog.fetch_list (SDKAdapter.models: models.with_raw_response.list, privacy=private, status=trained, project on every page) and pairs it through SDKCatalog.trained_models with the cached or in-flight public list; trained_catalog and trained_catalog_failed events checked against the current catalog, a failure kept apart from public lanes and retried only by the Trained chip or a refresh, and any unexpected worker failure reported as a generic failure with only its type logged; base descriptions through SDKCatalog.get (SDKAdapter.model: models.with_raw_response.retrieve, project in the query) only from the Trained chip of an open picker dialog (a trained list delivered after the dialog closed starts none), in lane order, at most 400 per lane and connection, batches of 10, one failure skipped and three in a row ending the scan with the sanitized reason, and a batch the main thread cannot apply ending its scan; trained_offers pairing records with detailed bases whose slot runs them and requiring strength bounds or a default for LoRAs; forms keeping IDs, kinds, strengths and a scope tag; trained_routes.apply rebuilding the payload on every request; strengths rounded to four decimals; and an installed test in which the form's payload and an MCP estimate_cost given the same parameters dry-run identical bytes. No SDK method, raw fallback, extension or dependency changed. Unit tests run the workers with scripted catalogs and the pure module with captured fixtures. Re-reviewed on 2026-10-12 the scan-retry sentence and the SDK paths it names: trained_models.on_bases marks only the models a scan reached as attempted, so the next Trained chip reads the ones a stopped scan never reached, and an explicit refresh (trained_models.request) clears the attempted set for failed ones; SDKCatalog.fetch_list and trained_models, SDKAdapter.models (privacy, status=trained for private models, project through _request) and SDKAdapter.model (models.with_raw_response.retrieve) were re-read unchanged in substance. The installed suite on macOS arm64 Blender 5.1.2 passed 1,452 tests (3 Windows-only skips), including the 24 tests of tests/blender/test_trained_models.py against a socket-free synthetic service with the captured public FLUX.1 Dev base and trained fixtures plus synthetic private records; the seven tests added for the review and desktop findings failed on the previous head. MCP trained listings and payload building from picks in the Image lane remain #97 work; render_form inspection lists the Render Image form's choice (docs-mcp.render-form-trained-models). No live read, dry run or paid run was made; private LoRAs and compositions, result quality, Blender 5.0 and 5.2, Linux, Windows and physical desktop interaction (mouse, keyboard, focus, screenshots) are not established.",
    "sources": {
      "docs/SDK_ADOPTION.md": "fd7c7990992bcac81de27556700048d7c8d8902f8982703b15cabfb72268490d",
      "scenario/core/jobs/manager.py": "b85840b0c66f18b4789daa5f6c27487ba50cd097eed81376f9973ee32529e8f9",
      "scenario/core/api/trained_offers.py": "0d9b84d0a9c956ceb7a9f5fe7df2fe6c3a5dbded4d6ef02e78e84c4e3456ac5b",
      "scenario/core/api/sdk_catalog.py": "84323d8e4ca6cbddcc4285a96711d235d5bf19f18d2c2e9a4207dc897a1da96f",
      "scenario/blender/trained_models.py": "a88fd498fac732f5cc2357159431c9c04e20b347bb700c14a7395a4abd4ce92e",
      "scenario/blender/model_picker.py": "70e7d37b136034358b1dcc110c2b44736bbfcaff021fcb11d8a7139782354d46",
      "scenario/blender/handlers.py": "0dccbbd97f2be476960f2709516989e6f218bd7372ef003c15138ddf6c737eb7",
      "scenario/blender/generation.py": "fb6af01e954f26b62e725e05ecb92906a4525d5858f78d6e1bfd90ce7aee332e",
      "tests/unit/test_trained_catalog_workers.py": "97b5b63442914ed13d04c31834fd9996e68bd53a37eb9ae92ba0c69a8c9cada7",
      "tests/unit/test_trained_offers.py": "c2f1e32790186449c44859d49b4a8b0f27483411c4dbcde0f2cff5473e0fe6dd",
      "tests/blender/test_trained_models.py": "e769078e8769dc375e0b7024b4b5358db08a21f8bbc880f6cf08697a66bf921c",
      "tests/blender/test_offline_runtime.py": "daf592f19255d371263812862759c19b8cb7b7ce045505c090280c0d2898b18e",
      "tests/blender/test_sdk_estimates.py": "b5d67fa9287208d997a3cbe75ca777f53c34eb32cf03f2aa5e3c727eac9ab1e5"
    }
  }
}
---

Evidence for [trained models in the native picker](../../SDK_ADOPTION.md#trained-models-in-the-native-picker).
