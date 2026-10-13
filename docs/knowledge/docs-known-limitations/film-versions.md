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
    "limits": "Reviewed on main 4dfca796 that film_review creates each review scene with bpy.data.scenes.new(title + ' / ' + mode.title() + ' Review'), so repeated final builds get Blender's .001 and .002 suffixes and no version label; that FilmExportCommands.inspect lists only review scenes whose scenario_production_id and scenario_recipe_sha256 match the current recipe, and FilmCaseStudyCommands inherits that filter; and that local_case_study.bundle_names derives the archive's top folder from the recipe title alone. A maintainer-authorized end-to-end run through local MCP on 3720c9e3 with two versions of one production met all three (private report). No fix or design was reviewed.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "50d988107d579b172936cd16b8d601e5d99fc46cb1e3929aabf685c9c0e2893a",
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
