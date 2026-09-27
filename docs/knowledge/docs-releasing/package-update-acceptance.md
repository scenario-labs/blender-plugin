---
{
  "type": "Evidence",
  "id": "docs-releasing.package-update-acceptance",
  "title": "Native update and Scenario package-state acceptance",
  "description": "Exact archive native install/update and durable state preservation in disposable profiles.",
  "evidence": {
    "path": "docs/RELEASING.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "limits": "Reviewed exact two-archive selection, newer-version rejection, shared disposable-profile/repository guards, explicit loopback file allowlist, package-state seeding/comparison, Python socket rejection, native upgrade and offline restart. The same candidate ZIP passed local package update/state checks on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS ARM64; the predecessor used the same package code with test-only older version metadata. This establishes local lifecycle behavior, not compatibility between published releases. The default synthetic fixture also passed Blender 5.0.1. Seven durable records across two credential scopes, six selected-scope job states, three staged upload states, exact prices/results/application origins, scope key, preferences and saved blend references were checked. No real credentials, Scenario requests or paid work were used. No release-pair provenance, hosted HTTPS flow, physical GUI controls, Windows/Linux package-mode acceptance, arbitrary-subprocess network sandbox or complete #37/#68 acceptance is claimed. The small synthetic CI fixture remains the default; actual-package mode requires explicit trusted archives and is not automatically exercised by that CI invocation.",
    "sources": {
      "tools/test_repository_update.py": "01ccc6452666f3b407749ecb536e562be3b73ce720679c61366c6cfd4197b63d",
      "tests/blender/repository_update.py": "55e16566ee539b8edb329056e13eada7f3cc3076b8c819d99e3e9c42c0d25244",
      "tests/blender/package_update.py": "58759e2e7a5882ebb51788d97c6e998fe0a5b1432401c1734b5000fe8cace4e3",
      "tests/unit/test_repository_update_runner.py": "bcda3eeb5ee1191a2eafee2fada50f65f62f1b8870d5c7b2ba98be499434cd0b"
    },
    "scope": "package-update-acceptance",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8"
  }
}
---

Evidence for [the release procedure](../../RELEASING.md).
