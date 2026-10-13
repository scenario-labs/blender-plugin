---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-versions",
  "title": "Several Film versions in one production",
  "description": "Final review scene names, current-recipe export and case-study sources, and case-study root folders named from the recipe title.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-versions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "4dfca796e1a082d89e0a0af091e78e161fa77fca",
    "limits": "Reviewed on main 4dfca796 that film_review creates each review scene with bpy.data.scenes.new(title + ' / ' + mode.title() + ' Review'), so repeated final builds get Blender's .001 and .002 suffixes and no version label; that FilmExportCommands.inspect lists only review scenes whose scenario_production_id and scenario_recipe_sha256 match the current recipe, and FilmCaseStudyCommands inherits that filter; and that local_case_study.bundle_names derives the archive's top folder from the recipe title alone. A maintainer-authorized end-to-end run through local MCP on 3720c9e3 with two versions of one production met all three (private report). No fix or design was reviewed. 2026-10-13 digest note: docs/KNOWN_LIMITATIONS.md was refreshed after the reference upload and required-argument fixes changed its workflow file inputs bullet and removed the fixed local MCP required-argument bullet; this topic's claims were not re-reviewed. 2026-10-13 digest note: refreshed after a follow-up to #436 synced the IME and saved audio bullets in docs/KNOWN_LIMITATIONS.md, the #97, #99 and #189 disposition rows in docs/maintenance/release-acceptance.md, and MAINTAINERS.md's ruleset bypass, immutable releases, Pages, social preview and admin checklist entries; this topic's claims were not re-reviewed. 2026-10-13 readability note: docs/KNOWN_LIMITATIONS.md was refreshed after the handbook readability rewrite added one bullet recording the repository installation verified for 0.10.0 and the pending release-to-release update check; this topic's text and claims were not re-reviewed, and the review date is unchanged. 2026-10-13 digest note: refreshed after in-extension audio playback changed this document's saved media text; this topic's claims were not re-reviewed.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "578692157fb0c906df0e44911f7c94353e59da242ae4afa57c548f0a020cd998",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d",
      "scenario/blender/film_export.py": "9e1bd807eee291de319408f442effa673c33ba0dcb401c07592c91ce60f3fbff",
      "scenario/blender/film_case_study.py": "eb2230af758604d492ee50fe4ba284c394e568894ab0cf3fabc85b0970afcd2b",
      "scenario/core/jobs/local_case_study.py": "802a60c338bdf0d25028a8d5bba494ac1fc41437dfcaddf13734a3203aac0e37"
    }
  }
}
---

# Several Film versions in one production

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#runtime-and-authentication).
