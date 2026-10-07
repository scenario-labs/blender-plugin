---
{
  "type": "Evidence",
  "id": "release-acceptance.project-update-state",
  "title": "Saved project scope native update acceptance",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "project-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03b070b9cb663b63cf8a411f6126efb40d4c66d0",
    "limits": "Observed the extended native probe with exact candidate 8d6c57231e35df5fe4349616875efe612de9039720d7b3df11eb014d872e915a and synthetic #319 predecessor ca6ffddc82a8a59d523255db76a27534973db6e6b15c8951fc4467ebcfa9f090 on macOS 27.0.1 arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Update and offline restart preserve the nonempty preference/runtime project, six selected jobs, other-key same-project job, four uploads and nonempty Film association. Default/alternate project lookups with the same credentials are isolated. All three report zero service calls, installed bytes verified, normal profiles unchanged, profiles removed and servers stopped. No package bytes, UI behavior, live project permissions or published release-pair acceptance changed. Original candidate installed/full-unit counts are not rerun claims for this test-only change.",
    "sources": {
      "tests/blender/package_update.py": "d226bacf1ee88a68c2912e7890db7144404f0c222c2ec4ee6e9e8b682ccf8727",
      "tests/unit/test_repository_update_runner.py": "54091880dec3597c3400c7342ef53e7bf681935ce81e9e3f1f8b6c199412726e",
      "tools/test_repository_update.py": "157ad33e1b12181db4d59d983272b894bfe5df45ec0b3b7622166431d5e3cf32",
      "docs/development/validation.md": "4e7b23457c80f5236645c05c6aa12c852ce9d18bc9f3bc23dca5f372f36ad2fa"
    }
  }
}
---

Evidence for [the release acceptance record](../../maintenance/release-acceptance.md).
