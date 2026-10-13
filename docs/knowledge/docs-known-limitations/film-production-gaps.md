---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-production-gaps",
  "title": "Film and Render Video gaps met by an end-to-end production run",
  "description": "Film captures and exports only scenes it builds, takes task media only from uploads or Film model tasks, and Render Video takes its motion reference only from a new capture.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-production-gaps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "4dfca796e1a082d89e0a0af091e78e161fa77fca",
    "limits": "Reviewed that FilmCaptureCommands.inspect in film_capture lists only scenes film_scene.matching_shot accepts for one recipe shot (production, recipe digest, shot and rate), that film_export's inspect lists only built review scenes of the current recipe, that film_tasks.model_task_request takes a task's references only from a saved Film upload association or a saved Film job, that the case-study ledger prices only saved Film jobs from their quote and leaves upload rows without a cost, and that render_references.prepare gives the Render Video scene role only a camera or viewport clip capture and the first frame only a file or a handed-off asset. The three gaps were met by a maintainer-authorized end-to-end production run through local MCP on main 3720c9e3 (private report: an artist-built timeline with cameras bound to markers, a rendered previz video, and generated takes uploaded again for Film). The statements describe current scope, not planned features; no fix or design was reviewed. Re-checked on 2026-10-13 after the rebase onto main at 4dfca796: #432 changed only the automatic preview bullet; the gaps bullet and its sources are unchanged. On 2026-10-13 the KNOWN_LIMITATIONS.md fingerprint was refreshed after other sections gained the second end-to-end run and three new limitation bullets; this topic's text is unchanged, as is the review date. 2026-10-13 digest note: docs/KNOWN_LIMITATIONS.md was refreshed after the reference upload and required-argument fixes changed its workflow file inputs bullet and removed the fixed local MCP required-argument bullet; this topic's claims were not re-reviewed. 2026-10-13 digest note: refreshed after a follow-up to #436 synced the IME and saved audio bullets in docs/KNOWN_LIMITATIONS.md, the #97, #99 and #189 disposition rows in docs/maintenance/release-acceptance.md, and MAINTAINERS.md's ruleset bypass, immutable releases, Pages, social preview and admin checklist entries; this topic's claims were not re-reviewed. 2026-10-13 readability note: docs/KNOWN_LIMITATIONS.md was refreshed after the handbook readability rewrite added one bullet recording the repository installation verified for 0.10.0 and the pending release-to-release update check; this topic's text and claims were not re-reviewed, and the review date is unchanged. 2026-10-13 digest note: refreshed after in-extension audio playback changed this document's saved media text; this topic's claims were not re-reviewed.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "578692157fb0c906df0e44911f7c94353e59da242ae4afa57c548f0a020cd998",
      "scenario/blender/film_capture.py": "a138817fd38a5c111c11e9bc96aaf9fc9ce525ab14d5a906f90dab41b6b2addf",
      "scenario/blender/film_export.py": "9e1bd807eee291de319408f442effa673c33ba0dcb401c07592c91ce60f3fbff",
      "scenario/core/jobs/film_tasks.py": "d32bc03d4ae47191ea0c90b540d70b780ba60b19fe30bd2962490d1478dcd473",
      "scenario/core/scene/film_case_study.py": "fe2a5758fb7ae634848e7d32752d1af4c7d7c59ab898e62d0d6d65a898df5874",
      "scenario/blender/render_references.py": "4897d8fe89d4bfbd9e171392cfa88feff4fa6a35ba88c40e4f63158fdb93aa47",
      "scenario/blender/render_lanes.py": "059119b06a18bcd0083c93dd51f00f923140db33776a2ccb56366e0ad78669b7"
    }
  }
}
---

# Film and Render Video gaps met by an end-to-end production run

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#runtime-and-authentication).
