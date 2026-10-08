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
    "limits": "Reviewed the isolated macOS launcher, native executable identity, offline startup, package/process evidence, owned-child cleanup and failure-path tests. Setup and observation exercised on macOS arm64 with Blender 5.0.1, 5.1.2 and 5.2.1. External desktop attachment remained intermittent; no complete keyboard, focus, UI workflow, other-platform or release acceptance is claimed.",
    "sources": {
      "tools/desktop_review.py": "548f9c1a18fff647920531212a84ea04d2ad0a4e94422cc874ddff927f99954a",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8",
      "tests/unit/test_desktop_review.py": "f08dbbcdd15d5a2690ccda842c0ade294cdfe7621d7c80e8af4aa55a7975ce4a",
      "tools/build.py": "162e00bb52f46770d219c5570d3ceccf3bd98e87055026c5a39944aec39f6bdd",
      "tools/blender_env.py": "53df246afea605b7c45f4c67296872a0d62571da3336268b6e84c303314eddde"
    }
  }
}
---

Evidence for [the contributor procedure](../../../CONTRIBUTING.md#interactive-desktop-review-on-macos).
