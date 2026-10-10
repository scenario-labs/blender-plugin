---
{
  "type": "Evidence",
  "id": "release-acceptance.protected-smoke",
  "title": "Protected aggregate-budget smoke execution",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "protected-smoke",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected shared suite quote/approval/resume and separately budget-authorized automation, exact aggregate arithmetic, durable exclusive suite attempts, failure-stop and scope guards. Reviewed main/repository/new-attempt workflow admission, required-reviewer/main-only environment checks, the plan and total cap frozen by admission, encryption preflight and ciphertext-only retention. Schedules always freeze the committed monthly plan and the fixed 40 CU cap and ignore inputs; dispatches choose the monthly or private plan with a cap defaulting to 40 CU, and only a private dispatch receives the private plan secret. budget-run refuses with exit 3 and no submission when the exact quoted total exceeds the cap. Offline tests use the real SDK adapter, coordinator and SQLite with mocked service responses; local GnuPG encryption/decryption and wrong-key rejection are exercised. Environment API readback on 2026-10-10 shows required reviewers and exactly the main branch policy; no repository setting, secret or variable was changed and no workflow was dispatched. The monthly plan's live reference upload, the first approved monthly run, any provider-side budget, hard-kill artifact preservation, native application and complete #40/#68 acceptance remain outside this review. Dated hosted-run evidence belongs to the release administration topic.",
    "sources": {
      "tools/smoke_suite.py": "7595c08b8c5bae299908f12c9124ab3f2376da0237203f0ecc937aaaf3c38a36",
      "tools/smoke_ci.py": "6cae0108faa854518fc932d7c6fb8b3a39a42ae4e255579f52abae2f1e2e0167",
      "tools/smoke_image.py": "683dbd2e8af3d18bd418ba318d2e3f03414bd7bf47486c366c2dd0fe24aff0ba",
      "tools/dev_config.py": "c3dbb5a4fb5c96a695f17cb436d15992f7b5efd11238c839d9ab44b9e9c7ac52",
      "tests/unit/test_smoke_suite.py": "efb342d8db2d5716233eb098ea1ed493b7dbfa4f1cc011c57088739e7d8f206c",
      "tests/unit/test_smoke_ci.py": "732dba269303b07c26468534960fbcc92a13ffddf265218c134c45153f67bab6",
      "tests/unit/test_smoke_monthly.py": "2b02eda1aae2455cf79b0c8570948035f2d214bfbb575686dd643c67b250d64d",
      "tests/unit/test_workflows.py": "e952780413f3d0ae69602ff996d9a2ba57818309bfa35e98fe380dc36a904d76",
      ".github/workflows/smoke.yml": "aeec8197a964fbce4f9dbe52096e857c62e714a7825af8c0c1ded38ea40fb6fe",
      "Makefile": "4a176bab88c63563c69f4812073f76040f7c03cca0730dab42a563399c600f72",
      "tests/smoke/README.md": "0be1d8f7c238cd243b9d4b8b7f1aa63ee5d32cbabda934f6fda06413e0f8b51d",
      "tests/smoke/monthly-plan.json": "c4d6c455b70fead30b8ac77be01e71b15174c44766196197a917af0012746f93",
      "tests/fixtures/models/model_patina-material.json": "281caebfa479542d14cd59e4861c91c0737653a869bd021d6cbd2d20d0be7dfa"
    }
  }
}
---

Evidence for [protected smoke execution](../../maintenance/release-acceptance.md).
