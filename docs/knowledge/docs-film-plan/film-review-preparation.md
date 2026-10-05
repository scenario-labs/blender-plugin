---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-review-preparation",
  "title": "Shared Film media preparation and explicit native application",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-review-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected shared worker copying/probing, scoped source revisions, optional matching master, bounded owner tickets, original recipe/scene checks, native generated-source claims, rollback and receipt-only recovery. Offline fixture and installed synthetic-media tests cover these command boundaries. Native/MCP presentation and explicit user approval controls, mixed-rate normalization, portable export, provider/human media quality and release acceptance remain pending. Private file stamps assume application-owned directories and are not hostile same-user filesystem isolation. Crashed processes can leave media for inspection. Only this preparation/application topic was reviewed.",
    "sources": {
      "scenario/core/jobs/film_review_media.py": "06a0719f8a6537fd561f3bf0878df5544c223bf82748773d014a4c7f9dab3eb4",
      "scenario/core/jobs/coordinator.py": "ef9e2946bf335502ab3bd59fd044a2fc872daca02aca96da51ac7fc8fd59a15a",
      "scenario/core/jobs/workers.py": "eadc85cd20d670ec4894e6c94544a823e32e78648507efa3021a2c65fe5a5469",
      "scenario/blender/job_session.py": "6da3cda9be9866dc0e63b9497cd158806afaab7a79a8f1bc4b40d47fec761ebe",
      "scenario/blender/film_review.py": "3948c973a1e8c30d7be5078f16b30a64677d95b50eedf3c2adef728d84818941",
      "tests/unit/test_film_review_media.py": "3c85a4b903d37c52ca91500575e70b4720170874eaf0ea1832f95b864917289e",
      "tests/blender/test_film_review_preparation.py": "9c8478b8948693e90313488be51cb0ab9c1f4d9a111a3d0f3cb1d9ad678223e6"
    }
  }
}
---

Source evidence for [FILM_PLAN](../../FILM_PLAN.md).
