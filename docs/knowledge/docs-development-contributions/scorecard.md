---
{
  "type": "Evidence",
  "id": "docs-development-contributions.scorecard",
  "title": "docs/development/contributions.md: scorecard",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/contributions.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-24",
    "limits": "Canonical contribution policy, including inspected Actions-only Dependabot configuration and commit-title compatibility; configuration does not prove live update delivery or administrative action-pin enforcement. Inspected the actions-pinned house-rule implementation, CLI and failure tests; this scoped offline convention check does not establish general YAML validity, release tag provenance, other house rules, REUSE coverage or administrative settings. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; full-tree prototype normalization, complete secret detection and repository protection remain separate. Scorecard workflow, publication restrictions and triage guidance inspected against the pinned upstream action documentation; public score, badge, SARIF publication and hosted acceptance require a successful default-branch run. Existing product and security claims retain their prior evidence.",
    "sources": {
      ".github/workflows/scorecard.yml": "3180f2d6860237bba70f189846d1aa3ad2e226f5d7476aca3c15887cb53a949c"
    },
    "scope": "scorecard",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/development/contributions.md: scorecard

Evidence for [the canonical document](../../development/contributions.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
