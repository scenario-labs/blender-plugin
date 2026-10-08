---
{
  "type": "Evidence",
  "id": "release-acceptance.candidate",
  "title": "Consolidated release candidate evidence",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "candidate",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "27bfb023b4cb90a06a0db0bdc8803038ae9145ee",
    "limits": "Preserves the initial development archive and its observed unit, installed native, synthetic predecessor/update/restart and non-submitting estimate results. Separately records the merged project-scope desktop archive and final runtime archive with their exact source/checksum identities; desktop and update proof are not transferred between archives. Reviewed current issue acceptance, parent CI and read-only branch/environment configuration. No paid result, live project override, other OS/DPI desktop, published release pair, public delivery or complete release acceptance is claimed. GitHub state is an observation on the review date and must be rechecked before release. The smoke_image.py fingerprint reflects a fresh source review of the current quote-bound material-map/count validation and resume checks, not a new live acceptance run. Historical archive identities remain unchanged; local reports remain private. Separately preserves retirement candidate 412e504a81721ded9369c7bedd887913e6bb8c92 and archive f4376ab6616e3dbfa59138416379fae9b58ed5663e2f6f53e226b6ac2b3b1fbb: 3839 unit tests with one known expected failure, 1051 installed tests per supported Blender version on macOS arm64 with two Windows-only skips, and same-archive synthetic update/restart with zero service requests and unchanged normal profiles. These historical results do not certify later parent fixes or the rebased branch.",
    "sources": {
      "docs/maintenance/release-plan.md": "55b496a4efc32a5294f4ffb38dc029227b0d5196c73f2267c184d688bf77f9fc",
      "docs/RELEASING.md": "12895529af30035fb49375bbc624043c8d8dedea9a5c5fe67be72af283ebe386",
      "docs/development/validation.md": "3db92d848f8cbddf38672e6b60950dc23ec1181139e861522a211731763239be",
      "tools/test_repository_update.py": "45fa8e414ac1436f09f01f17808be7f1c49e35080a6bd471fe2681c7bfc327ca",
      "tests/blender/package_update.py": "0e919d39511b395450f71997be01d32eaed4700b77bf55fa87786b185b7ea6d5",
      "tools/test_blender.py": "44fa88def4cad9ad823230ed207c2c5d6664db3913d8eb4cea4e53dfe4fc0eb2",
      "tools/smoke_model.py": "cf65eae775a588b784706505c8fe98169d83169fab026fc55d75e7739c16119b",
      "tools/smoke_image.py": "683dbd2e8af3d18bd418ba318d2e3f03414bd7bf47486c366c2dd0fe24aff0ba",
      ".github/workflows/blender-baseline.yml": "831c887cf2b56795e934a60d40fa3c9cd93de7d7d8cf2977589548ed01413022",
      "tests/blender/run_all.py": "3caa22c1a3e84b870c8c6f0c6ba51e7e9f503e1db1512073fde4e17ff0d15cd8",
      "docs/UI_STYLE.md": "a4d4afcbe008f1f50696560c369a19c470bc2daa14182dc2fce12df344a9b825",
      "scenario/core/jobs/manager.py": "688131a12cb5b7c8fde7d014ce2ceea131b17cd9dda279502e2aac4d9ea45707",
      "scenario/blender/runtime.py": "f85b53a9684831297fc07b6715d3286169c2713dc1116bbdb8220a979dcefe4f",
      "scenario/blender/pump.py": "aae6c6a454ef558d76ce5de90d08ced87f1f5904087d28f2d3ca49ed3bc1e11c",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/mcp/tools_scenario.py": "1d613605107ee7db59790faec37e8a3bd4ee8a014c38b00e0b44be20b67f12c3",
      "tests/blender/test_offline_runtime.py": "3429f261772abd43507d88a666ad9135a606c8927b20bf4e504c81c7d29c2c6e",
      "tests/blender/test_generation.py": "893b2601f6b694417878ad9d66a703fa6631f133090173b1a28687f135ae961a",
      "tests/blender/test_mcp_wait.py": "d6dd50e7b850e707bc8124665ecf415b84b51968c9ef02c4eb1fbffd4c2fad47"
    }
  }
}
---

Evidence for the [candidate acceptance record](../../maintenance/release-acceptance.md).
