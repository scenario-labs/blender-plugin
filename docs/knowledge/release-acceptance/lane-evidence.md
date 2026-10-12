---
{
  "type": "Evidence",
  "id": "release-acceptance.lane-evidence",
  "title": "0.10.0 offline, native and zero-spend evidence by lane",
  "description": "Unit, installed, hosted CI, desktop and free live evidence for each retained 0.10.0 lane.",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "lane-evidence",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "ff8d29d879487719fde8fd9b4089438ae0ba2c78",
    "limits": "Consolidates, per capability lane, the unit, installed native suite, hosted CI, physical desktop and free live evidence recorded between 2026-10-09 and 2026-10-12. Sources: private desktop and live reports (kept outside Git), the merged and open pull request descriptions #353 to #421, issue checklists #36, #38, #40, #64 to #66, #68, #97 to #99 and #189, and read-only GitHub reads of hosted CI run 38267887382 on main ff8d29d8 (6,691 unit tests with one expected failure on Python 3.11 and 3.13; 1,034 installed baseline tests per Linux x64 and Windows x64 job on Blender 5.0.1, 5.1.2 and 5.2.1, plus update and restart checks) and the failed weekly run 38204821594 (one stale test_result_actions expectation among 1,369 tests on macOS and Windows, corrected by #396). The 0.10.0 build from release PR #70 head 0bb206ef (ZIP e6740c84) is a pre-lane baseline: 1,149 installed tests per macOS arm64 Blender version and synthetic update and restart; its desktop journeys and free live quotes are recorded as reported, not rerun. Desktop evidence is macOS 27.0.1 arm64 Retina with a French layout, Blender 5.1.2 at UI scales 1.0 and 2.0 except the #70 build journeys on 5.0.1, 5.1.2 and 5.2.1; real CGEvent input driven by an agent harness with a spend guard, mostly on pre-merge or pre-rebase pull request heads whose merged code may differ. Free live checks used one test key in its default scope. No Linux or Windows desktop evidence, no Blender 5.0 or 5.2 desktop evidence for the lane PRs, and no final candidate identity exist: those fields are TODO placeholders for the final release candidate. Statuses are evidence summaries, not maintainer acceptance, release approval or issue closure. Source fingerprints identify the tooling and workflows behind the evidence kinds; they do not certify the observations.",
    "sources": {
      "docs/maintenance/release-acceptance.md": "7aed742285c254d80a8db19bca365fa17ce620cb7613d22fbed807fc6b851e3b",
      "docs/KNOWN_LIMITATIONS.md": "40654c5a1f5943fe87ce5d90b490b07681a754778e10e94ef6a7514c6ca45b1c",
      "tools/test_blender.py": "44fa88def4cad9ad823230ed207c2c5d6664db3913d8eb4cea4e53dfe4fc0eb2",
      "tools/test_repository_update.py": "3f79f680639001f74a626b86bcece1fde44dd2a9b463d6dc994e1c47e9c2ec6b",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "tests/blender/run_all.py": "4d819e8996ca41958227a311d8bf4d39d324846a4d666708da08f4c0e678057f",
      ".github/workflows/ci.yml": "9805ee9848f2eed06b0b9f108bcd7054592d61b431f8f4b57d4098f5cf43c344",
      ".github/workflows/blender-baseline.yml": "831c887cf2b56795e934a60d40fa3c9cd93de7d7d8cf2977589548ed01413022",
      ".github/workflows/blender-os.yml": "2a4303266ca0aacb374d1ec40c6e0b21a80acd7dae18d7b3956a3c42619412b1"
    }
  }
}
---

# 0.10.0 offline, native and zero-spend evidence by lane

Evidence for [the 0.10.0 evidence by lane](../../maintenance/release-acceptance.md#0100-evidence-by-lane).
