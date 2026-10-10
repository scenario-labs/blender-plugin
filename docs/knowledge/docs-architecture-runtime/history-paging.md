---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.history-paging",
  "title": "Cloud history paging",
  "description": "Every loaded cloud history row stays reachable in the panel and MCP.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "history-paging",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected cloud history paging. Core history keeps only custom jobs from each page; the panel draws every loaded row, keeps Load older while a cursor remains and labels a page that listed no generation; MCP list_generations reports more_loaded and older_page and loads the next page with older through the same cursor, pending-read and retry rules. A failed older read sets a separate older-page error and keeps the loaded rows and cursor, as Load older does: later list_generations calls return those rows with older_error and a note to retry with older, and only a repeated cursor points to refresh. Headless native tests cover 38 rows across two pages, a page without generations, MCP truncation and older paging, a failed older page whose follow-up call keeps the loaded rows and whose retry reads the same cursor, a cursor cycle that keeps its rows and asks for refresh, and argument validation. Free reads in one default API-key scope on 2026-10-10 showed a 50-row first page listing 22 generations after uploads, workflow runs and mesh preview renders were skipped, with older generations on the next page; there the SDK type filter returned no rows for custom, workflow or upload jobs when combined with hideResults=false, which the history read sends, and returned all of them without it; the history read and its local job-type filtering are unchanged. Workflow runs remain unlisted. No desktop scrolling review of long histories, other OS, release acceptance or #65 completion.",
    "sources": {
      "scenario/core/history.py": "70f03b84bd4eaa98712332b97ee492180d91f1663825e8f967cfbb7a9cfce781",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/blender/history.py": "4befae576dc242a24833ff84c3a9d73d341b538d891806d41ca8ca77a751cf7c",
      "scenario/blender/runtime.py": "7c975933ce6b54ff7683a17e34c47748fc7677b221b7e3cba2176bc091e215ef",
      "scenario/blender/panels.py": "582eb3bf8f9817854e14c957121b04f3383e1a24b7365258ee9ef7103a4e1957",
      "scenario/mcp/tools_scenario.py": "8a6aa7d4a22bef5f336cffe4f4d9ea0bf2b8362a86cc751e491a8396be2367d6",
      "tests/blender/test_sdk_history.py": "4664f0f36e34a4339b339137dbd68df01d7e9ce739f39007e4f3770756e17039"
    }
  }
}
---

# Cloud history paging

Evidence for [the canonical document](../../architecture/runtime.md).
