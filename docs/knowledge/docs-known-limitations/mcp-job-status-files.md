---
{
  "type": "Evidence",
  "id": "docs-known-limitations.mcp-job-status-files",
  "title": "Local MCP job_status files list",
  "description": "Shared job status lists files only for image results imported automatically in the current session.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "mcp-job-status-files",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "4dfca796e1a082d89e0a0af091e78e161fa77fca",
    "limits": "Reviewed on main 4dfca796 that ModelJobs.status reports files from the in-memory job view, and that the view's files are set only when the verify_results command delivers a READY job queued for automatic application, which imports image results; views rebuilt after a restart start with no files. So a ready video, an image not imported automatically and other result kinds list none, while results still name each asset, its media type and its download state without a path. Legacy registry records report their own files separately. Two maintainer-authorized end-to-end runs through local MCP met the empty list for ready video and image jobs (private report). 2026-10-13 digest note: docs/KNOWN_LIMITATIONS.md was refreshed after the reference upload and required-argument fixes changed its workflow file inputs bullet and removed the fixed local MCP required-argument bullet; this topic's claims were not re-reviewed. 2026-10-13 digest note: refreshed after a follow-up to #436 synced the IME and saved audio bullets in docs/KNOWN_LIMITATIONS.md, the #97, #99 and #189 disposition rows in docs/maintenance/release-acceptance.md, and MAINTAINERS.md's ruleset bypass, immutable releases, Pages, social preview and admin checklist entries; this topic's claims were not re-reviewed. 2026-10-13 readability note: docs/KNOWN_LIMITATIONS.md was refreshed after the handbook readability rewrite added one bullet recording the repository installation verified for 0.10.0 and the pending release-to-release update check; this topic's text and claims were not re-reviewed, and the review date is unchanged.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "41c3515a2844bf5ebd457ce99a9446d2a1dc11003941035fdaace38015f8c5c6",
      "scenario/blender/model_jobs.py": "956e032cbe134fc57a3f0aa2e996a1f06388b80f8f0561b16bd703763995240e",
      "scenario/mcp/tools_scenario.py": "112da784a70a39e76b052acc966f7378c924cb86ec3246a9fe0625685088d0f7"
    }
  }
}
---

# Local MCP job_status files list

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#runtime-and-authentication).
