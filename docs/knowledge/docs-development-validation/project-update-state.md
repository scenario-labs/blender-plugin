---
{
  "type": "Evidence",
  "id": "docs-development-validation.project-update-state",
  "title": "Project preference and storage across native updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "project-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03b070b9cb663b63cf8a411f6126efb40d4c66d0",
    "limits": "Scoped probe implementation review: requires a saved nonempty project preference and matching installed runtime scope, compares preferences/jobs/uploads after native upgrade and offline restart, rejects cross-project jobs/uploads/Film upload lookup and preserves same-project credential isolation. Unit fault injection covers missing/changed preference or runtime project and records leaked into default/alternate project scopes. Native results are recorded separately against exact archives. No provider authorization, live project permission check, desktop input, published release pair or prototype migration is claimed.",
    "sources": {
      "tests/blender/package_update.py": "d226bacf1ee88a68c2912e7890db7144404f0c222c2ec4ee6e9e8b682ccf8727",
      "tests/unit/test_repository_update_runner.py": "54091880dec3597c3400c7342ef53e7bf681935ce81e9e3f1f8b6c199412726e",
      "tools/test_repository_update.py": "157ad33e1b12181db4d59d983272b894bfe5df45ec0b3b7622166431d5e3cf32",
      "scenario/prefs.py": "b0fa6fe1f3f946ca8194980f8de31e6be1b080464be1b9107592b29d23dc939c",
      "scenario/blender/runtime.py": "f85b53a9684831297fc07b6715d3286169c2713dc1116bbdb8220a979dcefe4f",
      "scenario/core/jobs/credential_storage.py": "add164599e440041f76f94f9347114d829a0df3ef2e158cf533b8084805da074"
    }
  }
}
---

Evidence for [the validation guide](../../development/validation.md).
