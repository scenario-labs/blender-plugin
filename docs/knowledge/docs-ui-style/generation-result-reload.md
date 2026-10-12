---
{
  "type": "Evidence",
  "id": "docs-ui-style.generation-result-reload",
  "title": "Reload only recorded generation forms",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "generation-result-reload",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "f68a8175b000b6a3d13975d5f8d5b45ac376a8bc",
    "limits": "The result card and reload operator share a recorded-lane check. Film and generic model jobs without a supported lane or kind cannot overwrite a generation form. A recorded catalog lane without a native form never falls back to its asset kind's form; only generic jobs use the kind. Native regressions exercise the Film submission/result path, a generic model result, unchanged Image form state after direct invocation, retained explicit lane/kind fallback, and every catalog lane: each reloads into its own native form or offers no card action and leaves the current form unchanged on direct invocation. Existing image and edit-3D reload tests retain restoration coverage. No model-to-lane inference or Film recipe reload is introduced. Physical desktop verification remains separate from headless tests. On 2026-10-10 the test_splat_and_reload.py fingerprint was refreshed after it was reformatted and its point-cloud attribute assertion was renamed to splat_color for the shared builder; the reload and reference action tests are unchanged, and that refresh did not change the review date.",
    "sources": {
      "scenario/blender/generation.py": "60494c63c2ec9186d678087748ab56d3515d5d67195441df5d15fc5a6c97b5b7",
      "scenario/blender/operators.py": "59e1e3fb58435b45b40b6bdf06e7f1564dd8b9d1b90c97d71660e9379ee2d296",
      "scenario/blender/panels.py": "6865424bb96bd545a60a72ae5fad6531eccc97016fdd8eac21857d29eecf5415",
      "tests/blender/test_film_controls.py": "dfe026d71a93dcd5cd17f00e8c824b7189ada597b61300b4b8bfd9617c503b5a",
      "tests/blender/test_splat_and_reload.py": "57bb8a1793030b30352211c89944d0dfcff832fc9939a6b52502923b53e3f47a"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md#generations).
