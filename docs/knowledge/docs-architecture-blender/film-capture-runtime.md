---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.film-capture-runtime",
  "title": "Shared Film capture approval and upload handoff",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "film-capture-runtime",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Shared native/MCP local capture settings, once-only approval, bounded existing-worker admission, recipe/shot origin checks, retirement/cancellation and main-thread delivery. Separate upload approval validates the rendered content hash during staging and reuses existing SDK upload commands; no new endpoint or retry. Synthetic native coverage includes transient context pauses, stale/deleted sources, explicit recipe project, admission failure, cleanup, read-only drawing and uncertain-upload non-replay. Local capture files/reviews expire with the session; stored uploads remain. Desktop layout/input/focus/viewport, sustained GPU/audio, human motion review, live provider acceptance, finishing/export and integrated release acceptance remain pending. This topic does not approve the draft UI or certify the full document.",
    "sources": {
      "scenario/blender/film_capture.py": "e9f9b17f45a30623f52cee552d5e82c98634f18dc45450abb66376b05b8be090",
      "scenario/blender/film_capture_controls.py": "a1d516cef462a8ff1c1cc0d753d887307cb6e31836c068d7eb871c458baf58d4",
      "scenario/blender/film.py": "f1d83d6e620c96f9bbe3e54c22d8c0a0e994090041fb7ca4cccb43d871c15d5b",
      "scenario/blender/job_session.py": "5eef77a8c918404af2bdd938281af54c20fdd7650f21a5ef6221514224f5729f",
      "scenario/blender/runtime.py": "1a04ba756446ce08ca88d24414f027f9103eb04e5700b42e9d12f7f0b653ed0c",
      "scenario/blender/reference_uploads.py": "00aec147e040a08dd1e79deb7a4cece57fcf6e21fff277b11f25ba62acabf607",
      "scenario/core/jobs/coordinator.py": "411bb1e2a1fe9de16f14b543f57ecfbd4f41bb30299b7a04d0fd028c99fe8b0c",
      "scenario/core/jobs/workers.py": "b9fc73d93bc4045e21af461e11de56d16cd5a5afea8d3a23c7980590fc8eb3c8",
      "scenario/core/jobs/upload_sources.py": "12411cb18a7c27a271e864fef98aa8f7f1d9345966297757fe85dc0b2028e971",
      "scenario/core/jobs/uploads.py": "15aeb2d5501c190fa408fdc4eacaa7e667282232af729b69ebced751408eb55c",
      "scenario/mcp/tools_scenario.py": "e20e2e83158180aac290bc2e33a2d4892e3c99bc9f38694f08b954306b44d17e",
      "tests/blender/test_film_capture.py": "32cc17a85dd19431d147f26d16a0fe589a4aa35eade2ed444053dbadd0e8dcfe",
      "tests/blender/test_mcp_contracts.py": "177a08e1a946e9ad065a942f947c3045f694f2572a7471d460683e7ca3711106",
      "tests/unit/test_job_workers.py": "99189cfb291f9f1ea8fb0d1f44575b96d46e71c7898bf10ea8fcd18dc41362b7",
      "tests/unit/test_upload_sources.py": "ae8cdc0852592fee27e250a4a6c71dd471527c4ee190fd20c11249b00b613c0d",
      "tests/unit/test_mcp_descriptions.py": "5db5c5452101c4a5cb1dccae3b5afa1078d026473a3d309d59f85f11dccf6755",
      "tests/blender/run_all.py": "136f24708c00418869e2f57934c1bc9c9fa076d2af1c87b6c562a274063454dc"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/blender.md).
