---
{
  "type": "Evidence",
  "id": "release-acceptance.protected-smoke",
  "title": "Protected aggregate-budget smoke execution",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "protected-smoke",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Inspected shared suite quote/approval/resume and separately budget-authorized automation, exact aggregate arithmetic, durable exclusive suite attempts, failure-stop and scope guards. Reviewed main/repository/new-attempt workflow admission, required-reviewer/main-only environment checks, frozen budget output, encryption preflight and ciphertext-only retention. Offline tests use the real SDK adapter, coordinator and SQLite with mocked service responses; local GnuPG encryption/decryption and wrong-key rejection are exercised. A private five-case Image/Material/Video/GLB/audio plan completed live model/schema and non-submitting estimate reads in the configured test key default scope; every local case report has no saved job or submission marker. No environment/secrets/settings were created, workflow dispatched, paid call made or hosted generation/result acceptance claimed. Local reference upload automation, a provider/account-wide monthly ledger, hard-kill artifact preservation, native application and complete #40/#68 acceptance remain outside this slice.",
    "sources": {
      "tools/smoke_suite.py": "4c2dce4ddee1d35b5b6b9c5900f4837b73bbece9b6e23f1ba811fa0e188c20ed",
      "tools/smoke_ci.py": "89a207725badb7c6d6dff3df54fd2a127b40c457b3954f429d451ea7cf88690a",
      "tools/smoke_image.py": "fc9d8b8494e8a125908702c9c09f72129f6aeb46ce91b21e5a67bb8b8ed63c9b",
      "tools/dev_config.py": "c3dbb5a4fb5c96a695f17cb436d15992f7b5efd11238c839d9ab44b9e9c7ac52",
      "tests/unit/test_smoke_suite.py": "62736f901c762974d4c6b196fed0c708116973f165147d4e7f0d5343288c8cb6",
      "tests/unit/test_smoke_ci.py": "ecfa46ec19959b1fb52ac5e457ae140035de9e286c666ab19dbc3ec0032889ad",
      "tests/unit/test_workflows.py": "e952780413f3d0ae69602ff996d9a2ba57818309bfa35e98fe380dc36a904d76",
      ".github/workflows/smoke.yml": "6e9b68cc53d30801c68c8e9856fad0263bdef320e728b70a976731531f90dfa9",
      "Makefile": "4a176bab88c63563c69f4812073f76040f7c03cca0730dab42a563399c600f72",
      "tests/smoke/README.md": "de0c9f028862e08b9141453adc4845d1fd3858b30c3efe08312a0347dc2c829d"
    }
  }
}
---

Evidence for [protected smoke execution](../../maintenance/release-acceptance.md).
