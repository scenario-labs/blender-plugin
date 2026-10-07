---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-review-preparation",
  "title": "Shared Film media preparation and explicit native application",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-review-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Inspected shared worker copying/probing, scoped source revisions, optional matching master, bounded owner tickets, original recipe/scene checks, native generated-source claims, rollback and receipt-only recovery. Confirmed rollback outcomes are saved before file cleanup; cleanup failures preserve pending receipt authority and require inspection. Offline fixture and installed synthetic-media tests cover these command boundaries. Native/MCP presentation and explicit user approval controls, mixed-rate normalization, portable export, provider/human media quality and release acceptance remain pending. Private file stamps assume application-owned directories and are not hostile same-user filesystem isolation. Crashed processes can leave media for inspection. Only this preparation/application topic was reviewed. Prepared rollback media stays with the session until failed receipts are saved, including receipt-only retry. Preparation and final-admission cleanup failures preserve the original exception and bounded directory ownership for joined-shutdown retries.",
    "sources": {
      "scenario/core/jobs/film_review_media.py": "2ce54bd8ff3a73cef8bdefc965a2659f7967fad7248c3588df8bf5845a6624cd",
      "scenario/core/jobs/coordinator.py": "026ec2802838c67969dfe54da6fa2a32ae59a28bcc0b5bf587e7831697899a41",
      "scenario/core/jobs/workers.py": "eadc85cd20d670ec4894e6c94544a823e32e78648507efa3021a2c65fe5a5469",
      "scenario/blender/job_session.py": "c030477b4c43880a757b37e7efcb2751d35d966ce019656edc94aba78b831afa",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d",
      "tests/unit/test_film_review_media.py": "779079569d48b3a6643a409b18cbf04a864fd7005a96c96e3087c9be60b91ebc",
      "tests/blender/test_film_review_preparation.py": "ecc2c83dd22c9cd8357e0c90328359698487b7d95e78a2d6091bddbd731f653b",
      "tests/blender/run_all.py": "3caa22c1a3e84b870c8c6f0c6ba51e7e9f503e1db1512073fde4e17ff0d15cd8"
    }
  }
}
---

Source evidence for [FILM_PLAN](../../FILM_PLAN.md).
