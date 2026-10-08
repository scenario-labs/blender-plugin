---
{
  "type": "Evidence",
  "id": "release-acceptance.protected-smoke",
  "title": "Protected aggregate-budget smoke execution",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "protected-smoke",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "a3510564d693f59ae9cfbc530b5e52c50858c076",
    "limits": "Inspected shared suite quote/approval/resume and separately budget-authorized automation, exact aggregate arithmetic, durable exclusive suite attempts, failure-stop and scope guards. Reviewed main/repository/new-attempt workflow admission, required-reviewer/main-only environment checks, frozen budget output, encryption preflight and ciphertext-only retention. Offline tests use the real SDK adapter, coordinator and SQLite with mocked service responses; local GnuPG encryption/decryption and wrong-key rejection are exercised. A private five-case Image/Material/Video/GLB/audio plan completed live model/schema and non-submitting estimate reads in the configured test key default scope; every local case report has no saved job or submission marker. No environment/secrets/settings were created, workflow dispatched, paid call made or hosted generation/result acceptance claimed. Local reference upload automation, a provider/account-wide monthly ledger, hard-kill artifact preservation, native application and complete #40/#68 acceptance remain outside this slice. Rebased suite fixtures use the recorded Patina map/output schema with an explicit basecolor/normal subset. Current material validation and recovery documentation were source-reviewed; historical live-estimate evidence is unchanged. Reserved suite-state case names are rejected before storage or service requests.",
    "sources": {
      "tools/smoke_suite.py": "e80011f0db6fb74a5a3db8ef42d189656feca12fd0975477f8ea5ebf3d731d3c",
      "tools/smoke_ci.py": "89a207725badb7c6d6dff3df54fd2a127b40c457b3954f429d451ea7cf88690a",
      "tools/smoke_image.py": "683dbd2e8af3d18bd418ba318d2e3f03414bd7bf47486c366c2dd0fe24aff0ba",
      "tools/dev_config.py": "c3dbb5a4fb5c96a695f17cb436d15992f7b5efd11238c839d9ab44b9e9c7ac52",
      "tests/unit/test_smoke_suite.py": "efb342d8db2d5716233eb098ea1ed493b7dbfa4f1cc011c57088739e7d8f206c",
      "tests/unit/test_smoke_ci.py": "ecfa46ec19959b1fb52ac5e457ae140035de9e286c666ab19dbc3ec0032889ad",
      "tests/unit/test_workflows.py": "e952780413f3d0ae69602ff996d9a2ba57818309bfa35e98fe380dc36a904d76",
      ".github/workflows/smoke.yml": "6e9b68cc53d30801c68c8e9856fad0263bdef320e728b70a976731531f90dfa9",
      "Makefile": "4a176bab88c63563c69f4812073f76040f7c03cca0730dab42a563399c600f72",
      "tests/smoke/README.md": "65d133a41f3e91e395d2e8be14972f7c1730b6931758fb658e2c7b8014d4c21f",
      "tests/fixtures/models/model_patina-material.json": "281caebfa479542d14cd59e4861c91c0737653a869bd021d6cbd2d20d0be7dfa"
    }
  }
}
---

Evidence for [protected smoke execution](../../maintenance/release-acceptance.md).
