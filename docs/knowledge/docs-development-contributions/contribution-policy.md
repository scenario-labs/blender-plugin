---
{
  "type": "Evidence",
  "id": "docs-development-contributions.contribution-policy",
  "title": "docs/development/contributions.md: contribution policy",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/contributions.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-25",
    "limits": "Canonical contribution policy, including inspected Actions-only Dependabot configuration and commit-title compatibility; configuration does not prove live update delivery or administrative action-pin enforcement. Inspected the actions-pinned house-rule implementation, CLI and failure tests; this scoped offline convention check does not establish general YAML validity, release tag provenance, other house rules, REUSE coverage or administrative settings. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; full-tree prototype normalization, complete secret detection and repository protection remain separate. Strict link workflow, canonical Markdown inventory, explicit authentication exceptions and scoped failure reporting reviewed with offline tests and a local network scan; hosted PR rejection and scheduled issue delivery remain separate acceptance. PR template, canonical summary guidance and the shared PR-summary skill were aligned around the user or maintainer effect, relevant actions and limitations. This is authoring policy, not proof of future generated-summary quality or human approval.",
    "sources": {
      ".github/pull_request_template.md": "eabbfd4605a186471b30522a2c26d538a25e2b7778ca5a59e0bd7fbdc4bbbc68",
      ".github/workflows/commitlint.yml": "b80890944a6acd659312d9f1eced37582b21da64f163849900ae8154005b29a2",
      ".github/workflows/pr-name.yml": "0e315b620212b21f3058eae7d173813190ab81fd929b5d1178772c2fdbbc79d6",
      "commitlint.config.ts": "a3f4eb2798279d823aee2523592781ba1b328295e7d9528875f8682f6bb56881",
      "tests/unit/test_conventions_docs.py": "b07164b35c741484b3c726d5fe263c974219045f30c43f3e1065885c993613b4",
      ".agents/skills/blender-pr-summary/SKILL.md": "2eb7eb1c8a1e5c2ae34a1085c2565f87ec0c0549d8d798748a6c53edaa593869"
    },
    "scope": "contribution-policy",
    "base_revision": "17ed3fc912f64f3dbd64720cdd82649c5162d2ce"
  }
}
---

# docs/development/contributions.md: contribution policy

Evidence for [the canonical document](../../development/contributions.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
