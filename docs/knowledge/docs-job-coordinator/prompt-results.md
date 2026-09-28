---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.prompt-results",
  "title": "Full prompt result recovery",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "prompt-results",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Reviewed recovery of full prompt text from known successful scoped jobs through SDK jobs.retrieve and assets.retrieve, including complete-preview gating, bounded UTF-8 storage download, private cleanup, exact job/asset identity and stale revision/owner rejection. 2867 offline unit tests passed with the known SDK authentication xfail. Native JobSession tests cover off-thread retrieval, original target delivery and stale-origin rejection. Exact ZIP/native matrix results are recorded in the PR. No paid calls, automatic prompt mutation, native approval controls, MCP tool activation or live result acceptance is established. Text remains on the service; this adds no persistent prompt cache, database schema or SDK fallback.",
    "sources": {
      "scenario/core/jobs/results.py": "b2e9a32bec4c4c24c97a89ae013497d67bbca8f87fab193e8b9752c1d326af3a",
      "scenario/core/jobs/transfers.py": "658d5cd1182e5e7d718fe5b49232da1d6711eb37ab6b548ca5cb21139e194eb6",
      "scenario/core/jobs/coordinator.py": "c89cb8b5c97f65055cdc86dd81ba05a286f6e124b7ec530c7edaab5db3ad07fd",
      "scenario/core/jobs/workers.py": "dc6217702297b6f22caa9c14525bd1b81687ff9516d71cac23358b78bcb989c2",
      "scenario/blender/job_session.py": "b6fccaf828a58ff28aa038d7781a0da33d5c1ada8a3a60bd5020e338c7a56938",
      "tests/unit/test_prompt_results.py": "ba634788b783f42791cec85daebba27338d182ac6b54e41e08282c25c0c9e36f",
      "tests/unit/test_result_transfers.py": "05180c1472105ed5ff9d981889089170f15d8c42c87a46b908793d0f75c404d7",
      "tests/blender/test_session_uploads.py": "09faa5f11eaba495662bb793844f9d8c3f99a519afe9ef39e945bee9753e9b09"
    }
  }
}
---

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
