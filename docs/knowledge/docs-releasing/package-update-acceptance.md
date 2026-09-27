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
    "limits": "Reviewed exact two-archive selection, newer-version rejection, shared disposable-profile/repository guards, explicit loopback file allowlist, package-state seeding/comparison, Python socket rejection, native upgrade and offline restart. The same candidate ZIP passed local package update/state checks on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS ARM64; the predecessor used the same package code with test-only older version metadata. This establishes local lifecycle behavior, not compatibility between published releases. The default synthetic fixture also passed Blender 5.0.1. Seven durable records across two credential scopes, six selected-scope job states, three staged upload states, exact prices/results/application origins, scope key, preferences and saved blend references were checked. No real credentials, Scenario requests or paid work were used. No release-pair provenance, hosted HTTPS flow, physical GUI controls, Windows/Linux package-mode acceptance, arbitrary-subprocess network sandbox or complete #37/#68 acceptance is claimed. The default CLI remains the small synthetic fixture. An explicit test-predecessor mode changes only two version declarations, retains exact candidate bytes, rejects ambiguous selections and records synthetic provenance. This mode passed local Blender 5.0.1. Linux/Windows CI now selects exactly one already-tested ZIP, runs the actual-package mode on each supported version and retains its reports/artifacts. Shell regressions cover absent/duplicate candidates, paths with spaces and failed command propagation; hosted execution remains a separate run-specific result. The probe inventories Windows storage through the extended path namespace, retaining all files when legacy directory enumeration cannot handle long paths; package receipt verification still uses the production APIs.",
    "sources": {
      "tools/test_repository_update.py": "45fa8e414ac1436f09f01f17808be7f1c49e35080a6bd471fe2681c7bfc327ca",
      "tests/blender/repository_update.py": "55e16566ee539b8edb329056e13eada7f3cc3076b8c819d99e3e9c42c0d25244",
      "tests/blender/package_update.py": "62cea1df8f2f97ce00e24301c9c5659e5d59e9eb4abba736f2eb5ceda5a52623",
      "tests/unit/test_repository_update_runner.py": "7b5eb8fcf9f161a7e0bff423211711333f97c02fbd66c9ec02ab63a7f9063bde",
      ".github/workflows/blender-baseline.yml": "831c887cf2b56795e934a60d40fa3c9cd93de7d7d8cf2977589548ed01413022",
      "tests/unit/test_workflows.py": "e952780413f3d0ae69602ff996d9a2ba57818309bfa35e98fe380dc36a904d76"
    },
    "scope": "package-update-acceptance",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8"
  }
}
---

Evidence for [the release procedure](../../RELEASING.md).
