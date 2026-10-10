---
{
  "type": "Evidence",
  "id": "docs-user-guide.sdk-connection-check",
  "title": "docs/USER_GUIDE.md: SDK connection check",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "sdk-connection-check",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed Test connection worker ownership, background completion delivery, selected credentials, cache preservation, stale-event rejection and status icons against the current connection paths. Reviewed sanitized adapter status text: only HTTP 401, 403 and 429 add guidance, except that one model description read (SDKAdapter.model) answered with HTTP 403 or 404 raises AdapterUnavailable, so the form reads \"Could not load this model: This model is not available to the selected credentials or project (HTTP n)\" with that status kept; Test connection lists models and is unaffected. HTTP 401 and 403 ask to check the selected key and secret without naming a credential source, so the text also fits environment credentials; a 403 names the Project ID only when that request carried the override (unscoped discovery never does); HTTP 429 asks to retry later; other statuses keep the generic HTTP text. Each of these guided status sentences fits one 36-character sidebar line; the longer AdapterUnavailable sentence does not. Messages are fixed strings without response bodies, URLs, credentials or IDs. Preferences wraps the account label at 70 characters; the sidebar wraps catalog, price, generation and model-description errors at 36 characters, up to six lines. A failed model-description read keeps its \"Could not load this model:\" prefix, so a guided status sentence starts on the first wrapped line and can end on the second, while the AdapterUnavailable text wraps to four lines, within the six-line limit; the form's offline refusal wraps the same way, and Retry loading model remains available online. The sidebar account strip and the composer status line remain single clipped lines. Re-reviewed after the model-description retry change: its retry operator, recorded read failures, description validation and failed-read reporting leave the connection check paths unchanged. 3944 offline unit tests pass with the known SDK authentication xfail. Exact ZIP 9ad4511350c8cbc60077783c52888fe903fc14d0359bf7634d3b7491119d94f2 passes 1164 installed tests (2 Windows-only skips) on Blender 5.1.2 macOS arm64. Blender 5.0.1/5.2.1 runs, desktop input/focus, captures of the current wording, live 401/403/429 responses, paid execution and account/project identity discovery are not claimed. Reported live checks returned 403 for both a wrong secret and a nonexistent Project ID, so 403 guidance names both causes; this review did not repeat them. Other guide topics retain their independent evidence limits. Re-reviewed against main after the trained-model catalog change (AdapterUnavailable for single model reads) and the prepared-job cancellation runtime change; the connection check paths are unchanged. A scoped re-inspection for the shared saved-job descriptor refactor found that scenario/blender/panels.py only moves the Jobs panel row unchanged into draw_active_job; status wrapping, the account strip and the connection check paths are unchanged. Re-reviewed on main after the asset organization writes, history kind derivation and Film review control changes: organization writes raise their own WriteRejected and WriteUncertain texts but have no UI or MCP caller yet, panels.py also derives history row kinds, runtime.py only adds the Film review poll and run_all.py only lists two new native modules; the guided status texts, the AdapterUnavailable mapping, status wrapping, the account strip and the connection check paths are unchanged. The 3944-test count and the exact ZIP run above predate these re-reviews, which ran no native suite. Scoped 2026-10-10 check of the native first-frame control, not a full re-review: render_lanes._draw_first_frame only adds a read-only From a saved result label under a Render Video first-frame slot with intact saved-result provenance; the drawing this topic covers is unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "scenario/core/jobs/manager.py": "f79ea01367faf949a139d7daaeb55ff47e58d86cc98fd58e5ed3c6bcfd6183ab",
      "scenario/blender/runtime.py": "64b6e702f91c80be66ee6378125745b2db1d10f583bddd9f449dd3a06d15b4f8",
      "scenario/blender/operators.py": "41a8a513e4adec195e56794c7430078a95a46ddc1c48e2e682a24d2ff656512f",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/blender/panels.py": "c47a4301db4e2383c240dc2bde3dc86fd1d7a910a43c2da4a02dad235e0539b3",
      "scenario/blender/render_lanes.py": "5063e428d5c66b7147ca96d1bd6bed954b657ec1ca9ae7308c4ff2e2ef9ff39a",
      "scenario/prefs.py": "569ef8524cb0ba9e7d8f5b46582d4903b05d96a7cbc6cf1f2b3216be23c4ba96",
      "tests/unit/test_sdk_adapter.py": "20d372f8b072a3aaee24a28357d491ddcfb349d70b7cd7d54d1dece1cfd24e85",
      "tests/unit/test_sdk_connection.py": "035b6e016c8149b1102dd230c299d685ca4cc4a9c63226bc37c30ca689199f1a",
      "tests/blender/test_sdk_connection.py": "ff09606d34370b665a104983f99cb6b1aad9553a7c743e5c7080af85251b75c4",
      "tests/blender/run_all.py": "fe9abbbfbae94c51ebb9355b2f7bb18ec296bdc9ba6902acfc86d2bc30999ae0"
    }
  }
}
---

Evidence for [the canonical document](../../USER_GUIDE.md).
