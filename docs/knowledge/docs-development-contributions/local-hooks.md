---
{
  "type": "Evidence",
  "id": "docs-development-contributions.local-hooks",
  "title": "docs/development/contributions.md: local hooks",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/contributions.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-24",
    "limits": "Canonical contribution policy, including inspected Actions-only Dependabot configuration and commit-title compatibility; configuration does not prove live update delivery or administrative action-pin enforcement. Inspected the actions-pinned house-rule implementation, CLI and failure tests; this scoped offline convention check does not establish general YAML validity, release tag provenance, other house rules, REUSE coverage or administrative settings. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; full-tree prototype normalization, complete secret detection and repository protection remain separate. Strict link workflow, canonical Markdown inventory, explicit authentication exceptions and scoped failure reporting reviewed with offline tests and a local network scan; hosted PR rejection and scheduled issue delivery remain separate acceptance.",
    "sources": {
      ".pre-commit-config.yaml": "680ea251ccacb8b228e41c104abec8d7400b732f7c4f21d9ee7c427b234fd7fd",
      "tests/unit/test_check_secrets.py": "2ad38e5b6d50171c91f9e47f90b6c9109f5b79e85fb220b685cb2bee9918bee7",
      "tests/unit/test_local_hooks.py": "b826d5dd189abd1071ceb4eb175787348f39d5272331dce5bafcbeb1a2374d3d",
      "tools/check_secrets.py": "14238ccb9d415688895a0fed19aad8d622a237bdc480385aeb9cb64e7329c2c6"
    },
    "scope": "local-hooks",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/development/contributions.md: local hooks

Evidence for [the canonical document](../../development/contributions.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
