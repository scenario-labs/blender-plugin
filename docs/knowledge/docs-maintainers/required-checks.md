---
{
  "type": "Evidence",
  "id": "docs-maintainers.required-checks",
  "title": "Required checks and smoke environment read-back",
  "evidence": {
    "path": "docs/MAINTAINERS.md",
    "scope": "required-checks",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "88b6b3ec8ebd5707581f6d39f0fd158c784873a2",
    "limits": "Scoped live ruleset read-back: ci-ok, pr-title and commits required from GitHub Actions; no integrity bypass; existing CodeQL/code-quality and review rules preserved. Smoke environment existence, reviewer and main-only policy plus secret names were inspected, not secret values or plan contents. Scheduled smoke budget and hosted execution remain unaccepted. Merge-gate proof is tracked in issue 45 and its documentation PR. No settings changes, paid calls, merging or release acceptance are claimed.",
    "sources": {
      ".github/workflows/ci.yml": "9805ee9848f2eed06b0b9f108bcd7054592d61b431f8f4b57d4098f5cf43c344",
      ".github/workflows/pr-name.yml": "0e315b620212b21f3058eae7d173813190ab81fd929b5d1178772c2fdbbc79d6",
      ".github/workflows/commitlint.yml": "b80890944a6acd659312d9f1eced37582b21da64f163849900ae8154005b29a2",
      ".github/workflows/smoke.yml": "71ea95047895ceefb2ac8220663b2f6ee5a4b2dcf56dd4a8b5c8f3cee9a7b9bb",
      "commitlint.config.ts": "a3f4eb2798279d823aee2523592781ba1b328295e7d9528875f8682f6bb56881"
    }
  }
}
---

Evidence for [the canonical document](../../MAINTAINERS.md).
