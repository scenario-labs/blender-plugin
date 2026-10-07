---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-recipe-contracts",
  "title": "Film recipe and scoped reference contracts",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-recipe-contracts",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "04f434d3ed1375d5a4d4669cb25508d0b74fc0f3",
    "limits": "Pure selected-source Film recipe and scene-template adoption with separate intake and formatting commits, followed by optional project override and exact JobScope reference adaptation. Unit tests cover bounded recipes, timing, continuity, audio segments, default API-key scope and every foreign-scope dimension. No active Film entry point, coordinator, persistence, capture, scene application, finish/export or paid operation is introduced. TaskAssets are caller observations; their construction from verified scoped saved results remains integration work. Existing installed-package regressions do not establish Film runtime or live/media/desktop acceptance. Source-duration and omitted-audio defaults remain explicitly inherited restrictions. Reviewed task-name bounds: overlong derived shot take names report the explicit field required, while existing defaults and explicit identities are preserved. Boundary regressions cover all three shot take kinds and maximum-length explicit names. Text caps also apply after punctuation normalization; impossible trim-plus-duration windows identify both fields before source-duration defaulting. Public recipe regressions cover each affected text field and both explicit and omitted source duration. Placeholder legend keys reject collisions after whitespace trimming; distinct normalized names retain order and content without mutating the input recipe. Both collision orderings and successful normalization have offline regressions. Review follow-up rejects non-string reference names/kinds and duplicate normalized scene-object names. Deep JSON that encodes successfully but exceeds Python recursion while copying or resolving reports ValueError. Unit regressions exercise all these boundaries without adding a new fixed nesting-depth limit.",
    "sources": {
      "scenario/core/scene/film_plan.py": "12335d7571f7cf77da5ae3c6c9f9eedc3f726880618385184fe379e17b9d7fc4",
      "scenario/core/scene/film_scene_plan.py": "7695918ebb7e59c789bc6f54fac4041e2516148d2dcd57b978bac893c57e8448",
      "scenario/core/jobs/store.py": "a1b579f9c804f2ef5594115b5a48980d6ac4d2b664abfc498c086bbb771450d7",
      "tests/unit/test_film_plan.py": "132311300377b042d723c108e5d6fb4aa8ea2e1e1a16bc46b7c384bd3be8c477",
      "tests/unit/test_film_scene_plan.py": "bb7eeba2ea2bbf099cc83bdd25251fce11afd2009b060ce84787b98c0ae73445"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
