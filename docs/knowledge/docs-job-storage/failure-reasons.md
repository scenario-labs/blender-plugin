---
{
  "type": "Evidence",
  "id": "docs-job-storage.failure-reasons",
  "title": "Failure reasons of shared jobs",
  "description": "The reason Scenario gives for a failed shared job, cleaned and shown in memory only.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "failure-reasons",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed scenario/core/jobs/failures.py against the pinned scenario-sdk 2.2.0 wheel (scenario/sdk-wheel-lock.json): JobMetadata declares error and hint as Optional[str] ('Eventual error for the job'; 'Actionable hint for the user explaining what went wrong and how to resolve it'), and the public job retrieval reference documents the same two fields. failures.reason reads them only for status failure, joins the hint only when it adds text, turns control, format, line and other space characters into single spaces, keeps a link's scheme, host and path without credentials, query or fragment, drops a query left on a link without a scheme and data URIs, replaces bearer and basic credentials, JSON web tokens and values after credential names with [redacted], cleans at most 4,096 characters per value and cuts the result to 400 characters, keeping or appending the first support id (error_ followed by 6 to 64 letters and digits with a capital or digit). failures.observe yields a RemoteFailure only for a failed record whose remote job ID equals the response jobId. ModelJobs._observe calls it after progress.observe for the same refresh, cancel and decision snapshots; a failing reading drops the reason and logs only its type. Each ModelJobs.poll sets a failed view's error to the reason while the record keeps its remote ID and revision, else to None. The coordinator itself is unchanged: refresh_remote commits failed and returns the retrieval as before. No captured failed-job response exists; unit tests derive a synthetic one from the recorded Patina job and validate it with the SDK's JobRetrieveResponse, and a coordinator test drives refresh_remote through the real adapter and checks that the database holds neither the message nor its id. The store schema, StoredJob fields and transitions are unchanged; the reason lives in ModelJobs._failures only, and unit and installed tests find neither the message nor its id in any saved file. Installed tests ran on macOS arm64 Blender 5.1.2 only. No live failure was reproduced: a server-side failure cannot be triggered on demand. PromptJobs and BlockoutJobs, cloud history rows and list_local_jobs show no reason; a job that failed before a restart shows none. No desktop interaction or screenshot of the wrapped reason is claimed (#66). Re-checked on 2026-10-13 after the rebase onto #424 (main dad196a85): its strip progress bar change in draw.py and its tests in test_composer_jobs.py leave these failure-reason statements unchanged, so every fingerprint was refreshed to the merged files and the base revision moved to that main. Re-checked on 2026-10-13 after a review finding: a value after a credential name is now kept only when it is exactly a support id under the case-sensitive pattern, quoted or not and before trailing punctuation, through the _named_credential callback; ERROR_, Error_, short, long, lowercase-only and hyphenated look-alikes are redacted. The id kept for the suffix is now searched after credential redaction (but before link cleaning, within the first 4,096 characters), so an id-shaped part of a redacted secret is never appended. New unit cases cover these and failed on the previous code; only the fingerprints of the files this change touched were refreshed.",
    "sources": {
      "scenario/core/jobs/failures.py": "d870a6345d2b11c3ace48137094c05e1770e37468e6fa40cd08cdf20ca26997a",
      "scenario/core/jobs/coordinator.py": "4f7172c38f6cab5b69131502b9c7d74fe8544d03b8371d752190fb6b25e312d5",
      "scenario/blender/model_jobs.py": "dfff40b871b3d4e31ebb66f28cbf92c5b016d476cc6a6ff4ba512ff774ac9ec9",
      "tests/unit/test_job_failures.py": "5304fc4aac5b805772fec17bff0e80b52b4c8dcd5deb2fb681291a93ad95a271",
      "tests/unit/test_job_coordinator.py": "271283be78f7e17dd479242ce4f12587ec62b5a692bc57fd37ae4e7e80c53565",
      "tests/fixtures/patina-copper-512/job.json": "6362ff219fc99e64d9d89edc31281c0efb68e3c3965ba5a53859698fa3189b73",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "tests/blender/test_model_generation.py": "87fb16faad8becbc3982b2ef03b956da6e0ccc2bf9155723ca236b559d509c70"
    }
  }
}
---

# Failure reasons of shared jobs

Evidence for [the canonical document](../../JOB_STORAGE.md).
