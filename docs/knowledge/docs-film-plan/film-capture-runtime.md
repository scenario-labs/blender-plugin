---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-capture-runtime",
  "title": "Shared Film capture approval and upload handoff",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-capture-runtime",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "04f434d3ed1375d5a4d4669cb25508d0b74fc0f3",
    "limits": "Shared native/MCP local capture settings, once-only approval, bounded existing-worker admission, recipe/shot origin checks, retirement/cancellation and main-thread delivery. Separate upload approval validates the rendered content hash during staging and reuses existing SDK upload commands; no new endpoint or retry. Synthetic native coverage includes transient context pauses, stale/deleted sources, explicit recipe project, admission failure, cleanup, read-only drawing and uncertain-upload non-replay. Local capture files/reviews expire with the session; stored uploads remain. Previously recorded desktop interaction, limited to its exact archive in UI_STYLE.md, passed on macOS arm64 Blender 5.1.2: native dimension input and approval cancellation, real offline still rendering, synthetic upload approval/cancellation with matching captured/staged/transferred bytes, imported-upload inspection, discard cancellation and cleanup preserving the upload, and viewport selection/zoom. Original scenes/settings and the normal profile remain unchanged. This is bounded still interaction with mocked service/storage transport. Desktop video cancellation, sustained GPU/audio, human motion review, live uploads, other OS/DPI, finishing/export and integrated release acceptance remain pending. This topic does not certify the full document. MCP cancellation is dispatched before polling so finished undelivered renders can be dropped in the current recipe scene. Failed or canceled durable uploads enter review, allowing capture cleanup after workers finish while preserving the upload record and staged source. Native regressions cover both undelivered render states, authoritative server failure and prepared-upload cancellation without replay. Injected OS cleanup failures verify manual discard retains an explicit retry handle and session shutdown retires normally while keeping failed cleanup ownership. Worker-wait helpers document their intentional failure-outcome handling. Cleanup regressions now run the actual TemporaryDirectory.cleanup method, inject its inner removal failure and verify the detached-finalizer state before a successful explicit retry on all supported bundled Python versions.",
    "sources": {
      "scenario/blender/film_capture.py": "e9ac9e0049408e53785707ad386536d9126a9eaccf7c7aa01b5d36479b8e8033",
      "scenario/blender/film_capture_controls.py": "a1d516cef462a8ff1c1cc0d753d887307cb6e31836c068d7eb871c458baf58d4",
      "scenario/blender/film.py": "f1d83d6e620c96f9bbe3e54c22d8c0a0e994090041fb7ca4cccb43d871c15d5b",
      "scenario/blender/job_session.py": "5eef77a8c918404af2bdd938281af54c20fdd7650f21a5ef6221514224f5729f",
      "scenario/blender/runtime.py": "1a04ba756446ce08ca88d24414f027f9103eb04e5700b42e9d12f7f0b653ed0c",
      "scenario/blender/reference_uploads.py": "00aec147e040a08dd1e79deb7a4cece57fcf6e21fff277b11f25ba62acabf607",
      "scenario/core/jobs/coordinator.py": "411bb1e2a1fe9de16f14b543f57ecfbd4f41bb30299b7a04d0fd028c99fe8b0c",
      "scenario/core/jobs/workers.py": "b9fc73d93bc4045e21af461e11de56d16cd5a5afea8d3a23c7980590fc8eb3c8",
      "scenario/core/jobs/upload_sources.py": "12411cb18a7c27a271e864fef98aa8f7f1d9345966297757fe85dc0b2028e971",
      "scenario/core/jobs/uploads.py": "15aeb2d5501c190fa408fdc4eacaa7e667282232af729b69ebced751408eb55c",
      "scenario/mcp/tools_scenario.py": "97748df796554e5498de455a1d6ab20280a8f8e96cdae8df0e30120d62ee0cd7",
      "tests/blender/test_film_capture.py": "cac061b7d2b490712a8641533f3b4c448063f6d867d6725aeeb1114073206785",
      "tests/blender/test_mcp_contracts.py": "177a08e1a946e9ad065a942f947c3045f694f2572a7471d460683e7ca3711106",
      "tests/unit/test_job_workers.py": "99189cfb291f9f1ea8fb0d1f44575b96d46e71c7898bf10ea8fcd18dc41362b7",
      "tests/unit/test_upload_sources.py": "ae8cdc0852592fee27e250a4a6c71dd471527c4ee190fd20c11249b00b613c0d",
      "tests/unit/test_mcp_descriptions.py": "5db5c5452101c4a5cb1dccae3b5afa1078d026473a3d309d59f85f11dccf6755",
      "tests/blender/run_all.py": "136f24708c00418869e2f57934c1bc9c9fa076d2af1c87b6c562a274063454dc"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
