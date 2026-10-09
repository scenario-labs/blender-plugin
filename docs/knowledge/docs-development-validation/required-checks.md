---
{
  "type": "Evidence",
  "id": "docs-development-validation.required-checks",
  "title": "Required CI context identity",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "required-checks",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "88b6b3ec8ebd5707581f6d39f0fd158c784873a2",
    "limits": "Inspected the CI aggregator and separately reported title/commit checks against live required context names. The workflow does not configure rulesets. Runtime, provider and native acceptance are unchanged.",
    "sources": {
      ".github/workflows/ci.yml": "9805ee9848f2eed06b0b9f108bcd7054592d61b431f8f4b57d4098f5cf43c344",
      ".github/workflows/pr-name.yml": "0e315b620212b21f3058eae7d173813190ab81fd929b5d1178772c2fdbbc79d6",
      ".github/workflows/commitlint.yml": "b80890944a6acd659312d9f1eced37582b21da64f163849900ae8154005b29a2"
    }
  }
}
---

Evidence for [the canonical document](../../development/validation.md).
