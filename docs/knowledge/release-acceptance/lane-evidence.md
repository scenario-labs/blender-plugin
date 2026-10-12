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
    "base_revision": "2e89cae89f1ddc7de8487b938b683a57c472a2df",
    "limits": "Consolidates, per capability lane, the unit, installed native suite, hosted CI, physical desktop and free live evidence recorded between 2026-10-09 and 2026-10-12. Sources: private desktop and live reports (kept outside Git), the merged and open pull request descriptions #353 to #421, issue checklists #36, #38, #40, #64 to #66, #68, #97 to #99 and #189, and read-only GitHub reads of hosted CI run 38267887382 on main ff8d29d8 (6,691 unit tests with one expected failure on Python 3.11 and 3.13; 1,034 installed baseline tests per Linux x64 and Windows x64 job on Blender 5.0.1, 5.1.2 and 5.2.1, plus update and restart checks) and the failed weekly run 38204821594 (one stale test_result_actions expectation among 1,369 tests on macOS and Windows, corrected by #396). The 0.10.0 build from release PR #70 head 0bb206ef (ZIP e6740c84) is a pre-lane baseline: 1,149 installed tests per macOS arm64 Blender version and synthetic update and restart; its desktop journeys and free live quotes are recorded as reported, not rerun. Desktop evidence is macOS 27.0.1 arm64 Retina with a French layout, Blender 5.1.2 at UI scales 1.0 and 2.0 except the #70 build journeys on 5.0.1, 5.1.2 and 5.2.1; real CGEvent input driven by an agent harness with a spend guard, mostly on pre-merge or pre-rebase pull request heads whose merged code may differ. Free live checks used one test key in its default scope. No Linux or Windows desktop evidence, no Blender 5.0 or 5.2 desktop evidence for the lane PRs, and no final candidate identity exist: those fields are TODO placeholders for the final release candidate. Statuses are evidence summaries, not maintainer acceptance, release approval or issue closure. Source fingerprints identify the tooling and workflows behind the evidence kinds; they do not certify the observations. Re-checked on 2026-10-12 after the rebase onto main at 2e89cae8, not a full re-review: read-only GitHub reads showed #403 to #406, #408, #409, #416 to #420 and #422 merged on 2026-10-12 and #410, #411 and release PR #70 open, and hosted CI run 38314348872 on main 2e89cae8 passed (7,191 unit tests with one expected failure on Python 3.11 and 3.13; 1,139 installed baseline tests with five skips per Linux x64 and Windows x64 job on Blender 5.0.1, 5.1.2 and 5.2.1, with the install, update and restart checks). Lane statuses and pending owners follow those states; no desktop or live check of the merged code was added except the preview pager check. That private desktop check, dated 2026-10-13 in its report and run from about 22:15 to 22:31 UTC on 2026-10-12, installed an exact ZIP built from main 2e89cae8 (SHA-256 97027502) on macOS arm64 Blender 5.1.2 at UI scales 1.0 and 2.0 with real CGEvent input, Online Access disabled, the spend guard on and synthetic saved jobs seeded offline: paging, the disabled end arrows, the range line, no pager for four results, and viewport input and keyboard focus after an arrow click passed in Jobs, Generations and Studio (Results page at 1.0 only); in the default-width sidebar at both scales the arrows were about 1.65 times as tall as the 30% smaller tiles, and its fix, #423, was open when checked. main's test_repository_update adds Environment and trained-selection state expectations and run_all adds baseline modules and a per-test watchdog; neither changes what the evidence kinds mean.",
    "sources": {
      "docs/maintenance/release-acceptance.md": "ae1b2f85a8bec5e58440f7124a6d297f772f027e87a64b02a2f88bf5602da6f6",
      "docs/KNOWN_LIMITATIONS.md": "fd6377dc11ae0657bd59a97e4216a43718210dfcfb1bb27d50fc6557fa5f92bb",
      "tools/test_blender.py": "44fa88def4cad9ad823230ed207c2c5d6664db3913d8eb4cea4e53dfe4fc0eb2",
      "tools/test_repository_update.py": "66b853ded4a0e380f897427f2967a96346b8147e8ed2759f56a1ccd61e0fc6e3",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "tests/blender/run_all.py": "ab3d61ec67533a9abae8bb2983ba1a1c78b67acc311316564b107a155275e603",
      ".github/workflows/ci.yml": "9805ee9848f2eed06b0b9f108bcd7054592d61b431f8f4b57d4098f5cf43c344",
      ".github/workflows/blender-baseline.yml": "831c887cf2b56795e934a60d40fa3c9cd93de7d7d8cf2977589548ed01413022",
      ".github/workflows/blender-os.yml": "2a4303266ca0aacb374d1ec40c6e0b21a80acd7dae18d7b3956a3c42619412b1"
    }
  }
}
---

# 0.10.0 offline, native and zero-spend evidence by lane

Evidence for [the 0.10.0 evidence by lane](../../maintenance/release-acceptance.md#0100-evidence-by-lane).
