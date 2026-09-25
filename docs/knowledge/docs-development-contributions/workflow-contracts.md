---
{
  "type": "Evidence",
  "id": "docs-development-contributions.workflow-contracts",
  "title": "docs/development/contributions.md: workflow contracts",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/contributions.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-24",
    "limits": "Canonical contribution policy, including inspected Actions-only Dependabot configuration and commit-title compatibility; configuration does not prove live update delivery or administrative action-pin enforcement. Inspected the actions-pinned house-rule implementation, CLI and failure tests; this scoped offline convention check does not establish general YAML validity, release tag provenance, other house rules, REUSE coverage or administrative settings. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; full-tree prototype normalization, complete secret detection and repository protection remain separate. Strict link workflow, canonical Markdown inventory, explicit authentication exceptions and scoped failure reporting reviewed with offline tests and a local network scan; hosted PR rejection and scheduled issue delivery remain separate acceptance.",
    "sources": {
      "tests/unit/test_house_rules.py": "7eb4bf47fd5b93c89e4a4e2e43dc27eff3f273554a46b10756448deff14e3288",
      "tools/check_rules.py": "537a72a9fd58bc5eaccd0072d5b163eb7c0f2231de30ba52ce8cd84f703c3872"
    },
    "scope": "workflow-contracts",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/development/contributions.md: workflow contracts

Evidence for [the canonical document](../../development/contributions.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
