---
{
  "type": "Evidence",
  "id": "contributing.desktop-review",
  "title": "Isolated macOS desktop review",
  "evidence": {
    "path": "CONTRIBUTING.md",
    "scope": "desktop-review",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Reviewed the isolated macOS launcher, native executable identity, offline startup, package/process evidence, owned-child cleanup and failure-path tests, including final failure reporting when termination or reaping fails. Stable app identity from resolved source/artifact paths, fresh profiles and overlap locking are covered by offline tests; remembered desktop-control approval across runs has not been verified. Prior launcher setup and observation exercised on macOS arm64 with Blender 5.0.1, 5.1.2 and 5.2.1. External desktop attachment remained intermittent; no complete keyboard, focus, UI workflow, other-platform or release acceptance is claimed.",
    "sources": {
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8",
      "tests/unit/test_desktop_review.py": "7faef4fbf68d7bc19c34c970ef7d8fd756f2a1d8c505feae4ceb3625fd61f603",
      "tools/build.py": "162e00bb52f46770d219c5570d3ceccf3bd98e87055026c5a39944aec39f6bdd",
      "tools/blender_env.py": "53df246afea605b7c45f4c67296872a0d62571da3336268b6e84c303314eddde"
    }
  }
}
---

Evidence for [the contributor procedure](../../../CONTRIBUTING.md#interactive-desktop-review-on-macos).
