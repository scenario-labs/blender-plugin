---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.failure-reasons",
  "title": "Failure reasons of shared jobs",
  "description": "The reason Scenario gives for a failed shared job, cleaned and shown in memory only.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "failure-reasons",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed scenario/core/jobs/failures.py against the pinned scenario-sdk 2.2.0 wheel (scenario/sdk-wheel-lock.json): JobMetadata declares error and hint as Optional[str] ('Eventual error for the job'; 'Actionable hint for the user explaining what went wrong and how to resolve it'), and the public job retrieval reference documents the same two fields. failures.reason reads them only for status failure, joins the hint only when it adds text, turns control, format, line and other space characters into single spaces, keeps a link's scheme, host and path without credentials, query or fragment, drops a query left on a link without a scheme and data URIs, replaces bearer and basic credentials, JSON web tokens and values after credential names with [redacted], cleans at most 4,096 characters per value and cuts the result to 400 characters, keeping or appending the first support id (error_ followed by 6 to 64 letters and digits with a capital or digit). failures.observe yields a RemoteFailure only for a failed record whose remote job ID equals the response jobId. ModelJobs._observe calls it after progress.observe for the same refresh, cancel and decision snapshots; a failing reading drops the reason and logs only its type. Each ModelJobs.poll sets a failed view's error to the reason while the record keeps its remote ID and revision, else to None. The coordinator itself is unchanged: refresh_remote commits failed and returns the retrieval as before. No captured failed-job response exists; unit tests derive a synthetic one from the recorded Patina job and validate it with the SDK's JobRetrieveResponse, and a coordinator test drives refresh_remote through the real adapter and checks that the database holds neither the message nor its id. No new request: the reason comes from the existing jobs.with_raw_response.retrieve polling reply through SDKAdapter.job. Installed tests ran on macOS arm64 Blender 5.1.2 only. No live failure was reproduced: a server-side failure cannot be triggered on demand. PromptJobs and BlockoutJobs, cloud history rows and list_local_jobs show no reason; a job that failed before a restart shows none. No desktop interaction or screenshot of the wrapped reason is claimed (#66). Re-checked on 2026-10-13 after the rebase onto #424 (main dad196a85): its strip progress bar change in draw.py and its tests in test_composer_jobs.py leave these failure-reason statements unchanged, so every fingerprint was refreshed to the merged files and the base revision moved to that main.",
    "sources": {
      "scenario/core/jobs/failures.py": "1d793594f8324db9537a65866c8cd7b3b8bd4bd9607c1afc2086d40fac5d313b",
      "scenario/core/jobs/coordinator.py": "4f7172c38f6cab5b69131502b9c7d74fe8544d03b8371d752190fb6b25e312d5",
      "scenario/blender/model_jobs.py": "dfff40b871b3d4e31ebb66f28cbf92c5b016d476cc6a6ff4ba512ff774ac9ec9",
      "tests/unit/test_job_failures.py": "5c53924cc25c1b3678200b96e6ae42ef4743fb2f155f69f3d12038092a8af151",
      "tests/unit/test_job_coordinator.py": "271283be78f7e17dd479242ce4f12587ec62b5a692bc57fd37ae4e7e80c53565",
      "tests/fixtures/patina-copper-512/job.json": "6362ff219fc99e64d9d89edc31281c0efb68e3c3965ba5a53859698fa3189b73",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c"
    }
  }
}
---

# Failure reasons of shared jobs

Evidence for [the canonical document](../../SDK_ADOPTION.md).
