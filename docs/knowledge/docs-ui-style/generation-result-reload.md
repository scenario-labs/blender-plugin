---
{
  "type": "Evidence",
  "id": "docs-ui-style.generation-result-reload",
  "title": "Reload only recorded generation forms",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "generation-result-reload",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "88a6e2c296aba52f938501dbdabf259aef555127",
    "limits": "The result card and reload operator share a recorded-lane check. Film and generic model jobs without a supported lane or kind cannot overwrite a generation form. Native regressions exercise the Film submission/result path, a generic model result, unchanged Image form state after direct invocation, and retained explicit lane/kind fallback. Existing image and edit-3D reload tests retain restoration coverage. No model-to-lane inference or Film recipe reload is introduced. Physical desktop verification remains separate from headless tests. On 2026-10-10 the test_splat_and_reload.py fingerprint was refreshed after it was reformatted and its point-cloud attribute assertion was renamed to splat_color for the shared builder; the reload and reference action tests are unchanged, and the review date is unchanged.",
    "sources": {
      "scenario/blender/generation.py": "00d8436fbb222e8464d1b14c9d062f3d513914883edfdaa1b4ed261a1d6f1e02",
      "scenario/blender/operators.py": "8fb3a35beb010e81f4d4eaecf22688d8baf051ad88cdf2def50664e0da01a103",
      "scenario/blender/panels.py": "87cac7e9eedab5dc9a22000d8a76caadcaaa4328f283770d1be2f50a0928d6b8",
      "tests/blender/test_film_controls.py": "d2b4297e01f6815a85ba102d67bdbdb4800c7bbee30afead9987aa30e97b074e",
      "tests/blender/test_splat_and_reload.py": "57bb8a1793030b30352211c89944d0dfcff832fc9939a6b52502923b53e3f47a"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md#generations).
