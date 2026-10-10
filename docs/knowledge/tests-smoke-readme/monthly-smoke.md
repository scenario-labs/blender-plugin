---
{
  "type": "Evidence",
  "id": "tests-smoke-readme.monthly-smoke",
  "title": "Committed monthly smoke plan and fixed cap",
  "evidence": {
    "path": "tests/smoke/README.md",
    "scope": "monthly-smoke",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the committed version-2 monthly plan: default-scope project binding, one reference input with its recorded digest, one image case that uses it, a 512 by 512 Patina material case requesting all five maps and a short text-to-speech audio case. Reviewed admission that freezes the monthly plan and the fixed 40 CU cap for schedules, plan selection for dispatches, private plan secret isolation and aggregate refusal above the cap before any submission. Offline tests validate the plan, check the reference digest when the image is present, run the cases through budget-run against the recorded Gemini 3.1 Flash and Patina Material schemas and a synthetic speech schema, and cover an exact-cap fit and an over-cap refusal. Free dry-run quotes of the exact cases in the test key default scope on 2026-10-10 totalled 19.50 CU (10.75, 7.75 and 1 CU) without upload or submission, reusing an already imported reference asset. The reference image and the live upload transfer fix are separate changes. No scheduled, hosted or paid run, live upload, provider output, provider-side budget or complete #40/#68 acceptance is claimed.",
    "sources": {
      "tests/smoke/monthly-plan.json": "c4d6c455b70fead30b8ac77be01e71b15174c44766196197a917af0012746f93",
      "tools/smoke_ci.py": "6cae0108faa854518fc932d7c6fb8b3a39a42ae4e255579f52abae2f1e2e0167",
      "tools/smoke_suite.py": "7595c08b8c5bae299908f12c9124ab3f2376da0237203f0ecc937aaaf3c38a36",
      "tools/smoke_inputs.py": "3386ad525e8d9d9f4214dea1b6d05ec78084dfd02e00abf6305d904d2ef04526",
      "tools/smoke_image.py": "683dbd2e8af3d18bd418ba318d2e3f03414bd7bf47486c366c2dd0fe24aff0ba",
      ".github/workflows/smoke.yml": "aeec8197a964fbce4f9dbe52096e857c62e714a7825af8c0c1ded38ea40fb6fe",
      "tests/unit/test_smoke_ci.py": "732dba269303b07c26468534960fbcc92a13ffddf265218c134c45153f67bab6",
      "tests/unit/test_smoke_monthly.py": "2b02eda1aae2455cf79b0c8570948035f2d214bfbb575686dd643c67b250d64d",
      "tests/unit/test_smoke_inputs.py": "984ffec1a8a9d446290b5e51870d35d8211db6ebb756745e925a226563e5d85c",
      "tests/fixtures/models/model_google-gemini-3-1-flash.json": "3e086532d2546ebea8570d3af48a3c7fdbe4c9ac11c3ba7f8876bfdc1c784953",
      "tests/fixtures/models/model_patina-material.json": "281caebfa479542d14cd59e4861c91c0737653a869bd021d6cbd2d20d0be7dfa"
    }
  }
}
---

Evidence for [the monthly smoke plan](../../../tests/smoke/README.md#monthly-plan).
