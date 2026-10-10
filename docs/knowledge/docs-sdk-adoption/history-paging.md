---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.history-paging",
  "title": "Cloud history paging",
  "description": "History paging uses the same SDK job list cursor and filters job types locally.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "history-paging",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected cloud history paging. Core history keeps only custom jobs from each page; the panel draws every loaded row, keeps Load older while a cursor remains and labels a page that listed no generation; MCP list_generations reports more_loaded and older_page and loads the next page with older through the same cursor, pending-read and retry rules. Headless native tests cover 38 rows across two pages, a page without generations, MCP truncation and older paging, and argument validation. Free reads in one default API-key scope on 2026-10-10 showed a 50-row first page listing 22 generations after uploads, workflow runs and mesh preview renders were skipped, with older generations on the next page; there the SDK type filter returned no rows for custom, workflow or upload jobs when combined with hideResults=false, which the history read sends, and returned all of them without it; the history read and its local job-type filtering are unchanged. Workflow runs remain unlisted. No desktop scrolling review of long histories, other OS, release acceptance or #65 completion.",
    "sources": {
      "scenario/core/history.py": "70f03b84bd4eaa98712332b97ee492180d91f1663825e8f967cfbb7a9cfce781",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/blender/history.py": "3c9e76a4509b88eb3eccb26f3bb6323c759724b62c5b92f0b0f27f5f665a1b6b",
      "scenario/blender/panels.py": "582eb3bf8f9817854e14c957121b04f3383e1a24b7365258ee9ef7103a4e1957",
      "scenario/mcp/tools_scenario.py": "27ca5858dbd4374c3ec0c768d0042aa9967b33dfcbaccad65fe2f7c3ea5c2454",
      "tests/blender/test_sdk_history.py": "76de74cb134ef08a0c14b4584f7d36e7abc53db43272326abac4a27171ab97d5"
    }
  }
}
---

# Cloud history paging

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
