---
{
  "type": "Evidence",
  "id": "docs-mcp.history-paging",
  "title": "Cloud history paging",
  "description": "list_generations reports truncation and reads older pages explicitly.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "history-paging",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected cloud history paging. Core history keeps only custom jobs from each page; the panel draws every loaded row, keeps Load older while a cursor remains and labels a page that listed no generation; MCP list_generations reports more_loaded and older_page and loads the next page with older through the same cursor, pending-read and retry rules. A failed older read sets a separate older-page error and keeps the loaded rows and cursor, as Load older does: later list_generations calls return those rows with older_error and a note to retry with older, and only a repeated cursor points to refresh. Headless native tests cover 38 rows across two pages, a page without generations, MCP truncation and older paging, a failed older page whose follow-up call keeps the loaded rows and whose retry reads the same cursor, a cursor cycle that keeps its rows and asks for refresh, and argument validation. Free reads in one default API-key scope on 2026-10-10 showed a 50-row first page listing 22 generations after uploads, workflow runs and mesh preview renders were skipped, with older generations on the next page; there the SDK type filter returned no rows for custom, workflow or upload jobs when combined with hideResults=false, which the history read sends, and returned all of them without it; the history read and its local job-type filtering are unchanged. Workflow runs remain unlisted. No desktop scrolling review of long histories, other OS, release acceptance or #65 completion.",
    "sources": {
      "scenario/core/history.py": "1dac714c48e832ac110ed258d2496f038024eaa01faa7b9b942fc69a20400fa5",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/blender/history.py": "9474fcd97e4a9380bdde6a8427229544cf6581e35e84b2481942a6a38d0e7a98",
      "scenario/blender/runtime.py": "6b8d679498f3680d0563781a3b2a004f6b236b1831c36787695e8bafeaaba6b2",
      "scenario/blender/panels.py": "b3f13b99825957873acecfa0e59c42ad96da31abe070d85307556086d354344c",
      "scenario/mcp/tools_scenario.py": "2bbfed621f202d313835f3115d800c56cfe4c34614560af7003391059862cabf",
      "tests/blender/test_sdk_history.py": "b185e4e48412d48568599afd80e708eaf056dce94bcc8dabab504e684ce32902"
    }
  }
}
---

# Cloud history paging

Evidence for [the canonical guide](../../MCP.md).
