---
{
  "type": "Evidence",
  "id": "docs-job-storage.prompt-commands",
  "title": "Prompt Spark quote and submission commands",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "prompt-commands",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "65c48337d19c4f93127ad8c5e6f21f5e045f808c",
    "limits": "Reviewed the pinned SDK 2.2.0 public generate.prompt method and its raw-response wrapper. Offline contracts cover query/body aliases, exact Decimal quotes, selected project or credential-bound default scope, immutable input, durable claim before one submission, malformed/lost receipt uncertainty, replay rejection and read-only known-ID recovery after restart. Native JobSession regression covers the existing worker pool, input snapshot, persisted quote, single dispatch and stale-origin rejection. No raw API fallback, dependency change, live call, spending, UI activation, prompt text/asset delivery, remote prompt cancellation or prototype Spark replacement is established. Packaged macOS arm64 native validation is recorded in the PR; other OS/CPU and live release acceptance remain separate.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "2c1c4d8483275d5b92b0e3add35f7d1d85c1572734b1c7fe263a6846a6a516a5",
      "scenario/core/jobs/coordinator.py": "f05dae0f151462b7076a42c8335fc153aa55f5bc641977dc1a503b65249b342d",
      "scenario/core/jobs/store.py": "43ac06e793439096f4077b444971fa9b361f411221a69a56c1d9662a00b6f04d",
      "scenario/core/jobs/workers.py": "f9020b51ce6b138488c98b214cc248cf8679f0ee246176e72b7d0cd841d15468",
      "scenario/blender/job_session.py": "9a294bdff0fef54b13c2af5b9acf5042ddcedb08019ca598593599b68536fb32",
      "tests/unit/test_scenario_sdk_contract.py": "e604bdf00567edfe617bb669fc49095a2e18660ac838b3ad1a61b89ec2e62a1d",
      "tests/unit/test_sdk_adapter.py": "27bd1e66712b43e77aa2a757f81822e69ddd179ec66a1a03ebdea6df41e1f7c9",
      "tests/unit/test_job_coordinator.py": "12924a63c14a033c6a1bcef7883588986839c18a36fbc923489b234f14ac41d5",
      "tests/unit/test_job_cancellation.py": "f8207e678d357c0c73174af0d6444403e0231b082de937704b96e09d52a6b3f7",
      "tests/blender/test_session_uploads.py": "fd5e3252b1491d1264aad40fede081a323c8b9a781c96363772e1f4f458e6182"
    }
  }
}
---

Evidence for [the canonical guide](../../JOB_STORAGE.md).
