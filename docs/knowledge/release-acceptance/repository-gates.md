---
{
  "type": "Evidence",
  "id": "release-acceptance.repository-gates",
  "title": "Current repository gate configuration",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "repository-gates",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "88b6b3ec8ebd5707581f6d39f0fd158c784873a2",
    "limits": "Scoped correction of repository rules and protected smoke configuration against live read-back. Required ci-ok is enabled; smoke environment and required secret names exist. Secret values and private plan are not inspected; no scheduled budget is configured. Manual hosted run 37946893572 reports success, but its private plan and provider outcomes were not assessed here; hosted acceptance is not inferred. Existing candidate, provider, desktop and release evidence is not refreshed. Issue 45 retains live verification/documentation delivery until completed.",
    "sources": {
      "docs/MAINTAINERS.md": "e38ff4e967717882c5a38f8e108c4286da1cddbf43994684db7b11d496c1edd9",
      ".github/workflows/ci.yml": "9805ee9848f2eed06b0b9f108bcd7054592d61b431f8f4b57d4098f5cf43c344",
      ".github/workflows/smoke.yml": "71ea95047895ceefb2ac8220663b2f6ee5a4b2dcf56dd4a8b5c8f3cee9a7b9bb"
    }
  }
}
---

Evidence for [the canonical document](../../maintenance/release-acceptance.md).
