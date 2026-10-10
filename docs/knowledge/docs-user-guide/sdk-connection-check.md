---
{
  "type": "Evidence",
  "id": "docs-user-guide.sdk-connection-check",
  "title": "docs/USER_GUIDE.md: SDK connection check",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "sdk-connection-check",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed Test connection worker ownership, background completion delivery, selected credentials, cache preservation, stale-event rejection and status icons against the current connection paths. Reviewed sanitized adapter status text: only HTTP 401, 403 and 429 add guidance. HTTP 401 and 403 ask to check the selected key and secret without naming a credential source, so the text also fits environment credentials; a 403 names the Project ID only when that request carried the override (unscoped discovery never does); HTTP 429 asks to retry later; other statuses keep the generic HTTP text. Each status sentence fits one 36-character sidebar line. Messages are fixed strings without response bodies, URLs, credentials or IDs. Preferences wraps the account label at 70 characters; the sidebar wraps catalog, price, generation and model-description errors at 36 characters, up to six lines. A failed model-description read keeps its \"Could not load this model:\" prefix, so its status sentence starts on the first wrapped line and can end on the second; the form's offline refusal wraps the same way, and Retry loading model remains available online. The sidebar account strip and the composer status line remain single clipped lines. Re-reviewed after the model-description retry change: its retry operator, recorded read failures, description validation and failed-read reporting leave the connection check paths unchanged. 3944 offline unit tests pass with the known SDK authentication xfail. Exact ZIP 9ad4511350c8cbc60077783c52888fe903fc14d0359bf7634d3b7491119d94f2 passes 1164 installed tests (2 Windows-only skips) on Blender 5.1.2 macOS arm64. Blender 5.0.1/5.2.1 runs, desktop input/focus, captures of the current wording, live 401/403/429 responses, paid execution and account/project identity discovery are not claimed. Reported live checks returned 403 for both a wrong secret and a nonexistent Project ID, so 403 guidance names both causes; this review did not repeat them. Other guide topics retain their independent evidence limits. A scoped re-inspection for the shared saved-job descriptor refactor found that scenario/blender/panels.py only moves the Jobs panel row unchanged into draw_active_job; status wrapping, the account strip and the connection check paths are unchanged. The review date and earlier evidence are unchanged. Scoped 2026-10-10 check of the native first-frame control, not a full re-review: render_lanes._draw_first_frame only adds a read-only From a saved result label under a Render Video first-frame slot with intact saved-result provenance; the drawing this topic covers is unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "d2405048078890ff64037a359281ec1413cfd114e8bc599aa9bc29889f9638d3",
      "scenario/core/api/sdk_adapter.py": "5e81afa4ac8bd9e712e193037fae2bd2819f8d9a277089e7b622a038e910bba3",
      "scenario/core/jobs/manager.py": "f79ea01367faf949a139d7daaeb55ff47e58d86cc98fd58e5ed3c6bcfd6183ab",
      "scenario/blender/runtime.py": "43003d6a75ea5b11f2459ba56d39db94d43359a1cd1564765a10471d7979889e",
      "scenario/blender/operators.py": "41a8a513e4adec195e56794c7430078a95a46ddc1c48e2e682a24d2ff656512f",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/blender/panels.py": "ffff10ed5d252fca10c6da56156b5e364e0300cbdf88914120d7274d268402f8",
      "scenario/blender/render_lanes.py": "5063e428d5c66b7147ca96d1bd6bed954b657ec1ca9ae7308c4ff2e2ef9ff39a",
      "scenario/prefs.py": "569ef8524cb0ba9e7d8f5b46582d4903b05d96a7cbc6cf1f2b3216be23c4ba96",
      "tests/unit/test_sdk_adapter.py": "c03504aba6fc4848abababab2245a5cb93cc6f64be685a4967e8b1c4cc67ff30",
      "tests/unit/test_sdk_connection.py": "035b6e016c8149b1102dd230c299d685ca4cc4a9c63226bc37c30ca689199f1a",
      "tests/blender/test_sdk_connection.py": "ff09606d34370b665a104983f99cb6b1aad9553a7c743e5c7080af85251b75c4",
      "tests/blender/run_all.py": "0c167da4d582bd9eda230638ec4259ba22357c857ffd240b58485cbdd07a26a1"
    }
  }
}
---

Evidence for [the canonical document](../../USER_GUIDE.md).
