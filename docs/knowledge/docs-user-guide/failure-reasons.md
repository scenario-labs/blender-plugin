---
{
  "type": "Evidence",
  "id": "docs-user-guide.failure-reasons",
  "title": "Failure reasons of shared jobs",
  "description": "The reason Scenario gives for a failed shared job, shown only when it is plain text, in memory only.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "failure-reasons",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Reviewed on 2026-10-13 after the failure reason moved from redaction to an allowlist gate. scenario/core/jobs/failures.py reads metadata.error and metadata.hint, which the pinned scenario-sdk 2.2.0 wheel (scenario/sdk-wheel-lock.json) declares as Optional[str] on JobMetadata and the public job retrieval reference documents, only for status failure, through the existing jobs.with_raw_response.retrieve polling reply; the coordinator is unchanged. The module uses no regular expression: _normalize keeps at most 4,096 characters in NFC and turns control, format and space characters into single spaces; _showable accepts a part only when every character is a letter, a digit, a space or one of . , ; : ' \" ( ) - ! ? / % _, it has no //, and each space-separated token without surrounding punctuation passes _showable_token: an exact support id (_is_support_id: lowercase error_ and 6 to 64 ASCII letters and digits with a capital or digit), a Scenario resource id (_is_resource_id: model_, job_, asset_, team_, proj_, col_, workflow_, upload_ or apiu_ and 20 to 24 ASCII letters and digits, as fixtures show, or a model slug of 2 to 9 lowercase hyphenated words), a word of letters with inner hyphens or apostrophes shorter than 32 characters (_plain_word), or another token shorter than 12 characters with at most two letter/digit switches (_switches); a / only joins two words shorter than 12 characters, and _credential rejects tokens containing key, secret, token, password, passwd, pwd, auth, credential, signature, session or cookie, or sig alone, except _HARMLESS_WORDS. reason shows a showable part as it is, replaces another with NOT_SHOWN and returns UNREADABLE when no part is showable; nothing is extracted from a hidden part. Shown parts that contain each other are deduplicated both ways, and _bound cuts at a word boundary, never inside a support id, appending the shown text's first support id when the cut drops it. ModelJobs._observe_failure keeps the RemoteFailure in memory and each poll sets a failed view's error from it. tests/unit/test_job_failures.py holds an adversarial table with every leak raised in review and the shapes the gate targets, each of which yields only a fixed sentence, a readability table (the live error with its double space, a live hint, sizes, dates, percentages, model names and resource ids), token-rule cases, cut cases and a linear-time guard on pathological input; a coordinator test drives refresh_remote through the real adapter and checks the database keeps no message. The guide's statements on the red error control, the plain-text rule, the two fixed sentences, Copy error, the strip wording and restarts were checked against the code above. Installed tests ran on macOS arm64 Blender 5.1.2 only. No live failure was reproduced: a server-side failure cannot be triggered on demand. PromptJobs and BlockoutJobs, cloud history rows and list_local_jobs show no reason, and a job that failed before a restart shows none. No desktop interaction or screenshot is claimed (#66). Re-checked on 2026-10-13 after a seventh review: _showable_token now runs each side of a / pair through itself, so a side must also pass the plain-word, switch and credential rules, and _credential also matches credential words after translating digits that stand for letters (_LOOKALIKES: 0, 1, 3, 4, 5, 7 to o, i, e, a, s, t), so tok3n and s3ss10n are hidden alone or in a pair. New adversarial and token-rule cases (aB3kX9mQ2p/Zz8qW1vN4rT, x/sig, ok/s3ss10n, tok3n/abc, tok3n) failed on the previous code, and width/height, in/out and GPT/Image stay readable. Only the fingerprints of the files this change touched were refreshed. Re-checked on 2026-10-13 after an eighth review: _credential also tests each token with every non-alphanumeric character removed, as written and with the digit look-alike mapping, so a credential word split by a separator (github_tok/en, tok_en, to-ken, tok.en, pass/word, s/ecret, s/ig) is refused; the harmless allowlist applies to the joined form too (key-frame, author's). Support and resource ids are accepted before this check, so the live error's id stays shown. New adversarial and token-rule cases failed on the previous code. Only the fingerprints of the files this change touched were refreshed.",
    "sources": {
      "scenario/core/jobs/failures.py": "dde62be8446ee80f2255a73b326fbc64f1fc4d6e40261ea326d036dec2262499",
      "scenario/core/jobs/coordinator.py": "4f7172c38f6cab5b69131502b9c7d74fe8544d03b8371d752190fb6b25e312d5",
      "scenario/blender/model_jobs.py": "dfff40b871b3d4e31ebb66f28cbf92c5b016d476cc6a6ff4ba512ff774ac9ec9",
      "tests/unit/test_job_failures.py": "51cc32167bcb63259be64f55fbbf9b3effe2131144f4d651a6a5ff8788571b99",
      "tests/unit/test_job_coordinator.py": "271283be78f7e17dd479242ce4f12587ec62b5a692bc57fd37ae4e7e80c53565",
      "tests/fixtures/patina-copper-512/job.json": "6362ff219fc99e64d9d89edc31281c0efb68e3c3965ba5a53859698fa3189b73",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "scenario/core/ui/job_strip.py": "9526afc75d309886c8f7821b1250e6b5f6cb4d3f776b845417f563e8c485d0ab",
      "scenario/blender/panels.py": "4c6abf90ee51a52c867fd7a1ea0898060d995ea3fc4eac148c58a918031b7b7d",
      "scenario/blender/operators.py": "c4274af0155c9847b9911376727db70251aa09f7515e9ffe88774412ac7fc65d",
      "scenario/blender/composer/job_card.py": "da46878261589278aa0f4c2a7c777fa5e5fc78f24b021f5aa7cfe59396b00e0c",
      "scenario/blender/composer/draw.py": "682505bcd80104c20e7b0c2dbc2c48697c10aa8b1831fafdbf23488dc5c7d819",
      "scenario/blender/label_wrap.py": "3e0cf29b6d34332b42fe1dc8dd589a1b26b962ead15da1843b3327a568a4a849",
      "tests/unit/test_job_strip.py": "a5a29129792cd11012f241501c2ba0ceb38c684688c0e854fb87f41a91631260",
      "tests/blender/test_model_generation.py": "afcc4d5660b71adcb35f804ee99a85e45c1eabdf34d9057af0d83c15c8d7efc7",
      "tests/blender/test_composer_jobs.py": "03169b62b9b2ba29122476d86eb68021e94b4018921a8ba5d0fb3087fa5f6e16"
    }
  }
}
---

# Failure reasons of shared jobs

Evidence for [the canonical document](../../USER_GUIDE.md).
