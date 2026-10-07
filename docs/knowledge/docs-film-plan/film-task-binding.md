---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-task-binding",
  "title": "Durable Film model task binding",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-task-binding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Model-task quote preparation uses the existing scoped job store, SDK model commands, worker queue and native session. Schema 8 reserves scope/production/task with the spend intent; recipe and transitive dependency digests constrain completed result references. Unit and installed-package tests cover races, uncertainty, corruption, scope and scene guards. Upgrade probes compare actual schema 7 code in a synthetic version-only predecessor with the exact candidate. This is not published release-pair acceptance, live paid generation, native Film UI or MCP wiring, upload-task binding, production identity retention in views, finishing/export or human media/desktop acceptance. Recipe text is not persisted; integrations must retain the production identity and invalidate recipe edits. Existing low-level store trust and no-retry boundaries apply.",
    "sources": {
      "scenario/core/jobs/film_tasks.py": "fe19b05482bdff500f29a8f678338a766384ee1930324ccf4530b091a9779f85",
      "scenario/core/jobs/store.py": "761c17fa0ad7e0d49b895e07760051f4704e03878da8fdab5491d27b834ec57e",
      "scenario/core/jobs/coordinator.py": "51dfb48293fb4d79641fa6d1ea39c1670154cc9cbe76176203136a0b6101db44",
      "scenario/core/jobs/workers.py": "35b577061aee4f1016dce9bd20f8f4a486fe5e8daddfe3194296a6132acaf5f1",
      "scenario/blender/job_session.py": "0cea2f38b4070696e2a3e6fb6f9906223336a9e68adda546ad6dee6b8e2b650c",
      "tests/unit/test_film_jobs.py": "f9bbe57632e0c736d119b0af4f19f3cf8ce64bc1631fe5f833a2ead5e29c4e68",
      "tests/unit/test_job_store.py": "8c76839b221deae31f07ae057fa8b549baec5ce06e7b4830416ca68478437f62",
      "tests/blender/test_job_store.py": "f9d1b45d2060bb7e6ad22e507dbe694e8b48f7d3ff4495fd83af370c0fa6d601",
      "tests/blender/test_job_session.py": "de4e44ae13cc568458b241c1cbf1b89f65f2c0309742101d3d0ba12eac3de581",
      "tests/blender/package_update.py": "e4cd97c22de3ff0f9182607803798cb4ca1c791abbb7863fe89d9135b27bfce8",
      "tests/unit/test_repository_update_runner.py": "3b9b81005e911ad01e977ab222a9b6b1709dbbc547ca55614c1277f29c211c61"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
