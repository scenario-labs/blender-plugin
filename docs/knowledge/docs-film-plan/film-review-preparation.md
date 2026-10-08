---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-review-preparation",
  "title": "Shared Film media preparation and explicit native application",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-review-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "60f358d0e671a6096a21a08c04a463411c86a8b2",
    "limits": "Inspected shared worker copying/probing, scoped source revisions, optional matching master, bounded owner tickets, original recipe/scene checks, native generated-source claims, rollback and receipt-only recovery. Confirmed rollback outcomes are saved before file cleanup; cleanup failures preserve pending receipt authority and require inspection. Offline fixture and installed synthetic-media tests cover these command boundaries. Native/MCP presentation and explicit user approval controls, mixed-rate normalization, portable export, provider/human media quality and release acceptance remain pending. Private file stamps assume application-owned directories and are not hostile same-user filesystem isolation. Crashed processes can leave media for inspection. Only this preparation/application topic was reviewed. Prepared rollback media stays with the session until failed receipts are saved, including receipt-only retry. Preparation and final-admission cleanup failures preserve the original exception and bounded directory ownership for joined-shutdown retries. Retired session ownership survives unused-media cleanup errors; local paths are logged once, enabled reaping spaces retries by five seconds, and re-registration restarts cleanup after disable. Installed tests cover successful retirement, retry pacing and disable/enable recovery without network or replay. Consumed media after confirmed rollback or no native build is retained by the coordinator independently of weak receipt handles; explicit receipt recovery deletes it, while retirement cleans it without retrying receipts or changing durable inspection state. Deletion errors retain the retired cleanup owner; successful or uncertain native scenes keep their media. Installed regressions cover pending rollback receipts at file-load retirement, deletion retry, dropped receipt handles and pending success receipts.",
    "sources": {
      "scenario/core/jobs/film_review_media.py": "2ce54bd8ff3a73cef8bdefc965a2659f7967fad7248c3588df8bf5845a6624cd",
      "scenario/core/jobs/coordinator.py": "170c1c809b919369370f1a071d6f46d0365bfead4a3424d85ecf951077eb1e63",
      "scenario/core/jobs/workers.py": "eadc85cd20d670ec4894e6c94544a823e32e78648507efa3021a2c65fe5a5469",
      "scenario/blender/job_session.py": "4222888769015bf0c1b7b4a816942ff77da414b361adc23410da1b39dfdd1d5b",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d",
      "tests/unit/test_film_review_media.py": "9b0ad77327ac96f70c4114b7d3e9b062282a3b38b0899f3febf1e6d73ee0acc5",
      "tests/blender/test_film_review_preparation.py": "597cd4f1eab546d5aaa5420407aa08eaddfc352eaf40b99b7ed24527cdc1a613",
      "tests/blender/run_all.py": "3caa22c1a3e84b870c8c6f0c6ba51e7e9f503e1db1512073fde4e17ff0d15cd8"
    }
  }
}
---

Source evidence for [FILM_PLAN](../../FILM_PLAN.md).
