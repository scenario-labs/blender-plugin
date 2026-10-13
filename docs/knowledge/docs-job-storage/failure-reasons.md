---
{
  "type": "Evidence",
  "id": "docs-job-storage.failure-reasons",
  "title": "Failure reasons of shared jobs",
  "description": "The reason Scenario gives for a failed shared job, shown only when it is plain text, in memory only.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "failure-reasons",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed on 2026-10-13 after the failure reason moved from redaction to an allowlist gate. scenario/core/jobs/failures.py reads metadata.error and metadata.hint, which the pinned scenario-sdk 2.2.0 wheel (scenario/sdk-wheel-lock.json) declares as Optional[str] on JobMetadata and the public job retrieval reference documents, only for status failure, through the existing jobs.with_raw_response.retrieve polling reply; the coordinator is unchanged. The module uses no regular expression: _normalize keeps at most 4,096 characters in NFC and turns control, format and space characters into single spaces; _showable accepts a part only when every character is a letter, a digit, a space or one of . , ; : ' \" ( ) - ! ? / % _, it has no //, and each space-separated token without surrounding punctuation passes _showable_token: an exact support id (_is_support_id: lowercase error_ and 6 to 64 ASCII letters and digits with a capital or digit), a Scenario resource id (_is_resource_id: model_, job_, asset_, team_, proj_, col_, workflow_, upload_ or apiu_ and 20 to 24 ASCII letters and digits, as fixtures show, or a model slug of 2 to 9 lowercase hyphenated words), a word of letters with inner hyphens or apostrophes shorter than 32 characters (_plain_word), or another token shorter than 12 characters with at most two letter/digit switches (_switches); a / only joins two words shorter than 12 characters, and _credential rejects tokens containing key, secret, token, password, passwd, pwd, auth, credential, signature, session or cookie, or sig alone, except _HARMLESS_WORDS. reason shows a showable part as it is, replaces another with NOT_SHOWN and returns UNREADABLE when no part is showable; nothing is extracted from a hidden part. Shown parts that contain each other are deduplicated both ways, and _bound cuts at a word boundary, never inside a support id, appending the shown text's first support id when the cut drops it. ModelJobs._observe_failure keeps the RemoteFailure in memory and each poll sets a failed view's error from it. tests/unit/test_job_failures.py holds an adversarial table with every leak raised in review and the shapes the gate targets, each of which yields only a fixed sentence, a readability table (the live error with its double space, a live hint, sizes, dates, percentages, model names and resource ids), token-rule cases, cut cases and a linear-time guard on pathological input; a coordinator test drives refresh_remote through the real adapter and checks the database keeps no message. The store schema, StoredJob fields and transitions are unchanged; installed and unit tests find neither the message nor its id in any saved file. Installed tests ran on macOS arm64 Blender 5.1.2 only. No live failure was reproduced: a server-side failure cannot be triggered on demand. PromptJobs and BlockoutJobs, cloud history rows and list_local_jobs show no reason, and a job that failed before a restart shows none. No desktop interaction or screenshot is claimed (#66).",
    "sources": {
      "scenario/core/jobs/failures.py": "2e53d457618f894549d2f3c520c440eaec94c4444a1a81efe8a8e6961504f6c9",
      "scenario/core/jobs/coordinator.py": "4f7172c38f6cab5b69131502b9c7d74fe8544d03b8371d752190fb6b25e312d5",
      "scenario/blender/model_jobs.py": "dfff40b871b3d4e31ebb66f28cbf92c5b016d476cc6a6ff4ba512ff774ac9ec9",
      "tests/unit/test_job_failures.py": "266c6d83151894a28f9aa84a78378a6469be21ff80c159c6fc40cac4e12df613",
      "tests/unit/test_job_coordinator.py": "271283be78f7e17dd479242ce4f12587ec62b5a692bc57fd37ae4e7e80c53565",
      "tests/fixtures/patina-copper-512/job.json": "6362ff219fc99e64d9d89edc31281c0efb68e3c3965ba5a53859698fa3189b73",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "tests/blender/test_model_generation.py": "afcc4d5660b71adcb35f804ee99a85e45c1eabdf34d9057af0d83c15c8d7efc7"
    }
  }
}
---

# Failure reasons of shared jobs

Evidence for [the canonical document](../../JOB_STORAGE.md).
