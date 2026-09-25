---
{
  "type": "Evidence",
  "id": "docs-development-contributions.dependency-environment",
  "title": "docs/development/contributions.md: dependency environment",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/contributions.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-24",
    "limits": "Canonical contribution policy, including inspected Actions-only Dependabot configuration and commit-title compatibility; configuration does not prove live update delivery or administrative action-pin enforcement. Inspected the actions-pinned house-rule implementation, CLI and failure tests; this scoped offline convention check does not establish general YAML validity, release tag provenance, other house rules, REUSE coverage or administrative settings. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; full-tree prototype normalization, complete secret detection and repository protection remain separate. Strict link workflow, canonical Markdown inventory, explicit authentication exceptions and scoped failure reporting reviewed with offline tests and a local network scan; hosted PR rejection and scheduled issue delivery remain separate acceptance.",
    "sources": {
      ".github/dependabot.yml": "2d1ef5df890197205268c05d1fe1f54943f0b1d6984a2f7eb064f364c2c438d2",
      "pyproject.toml": "d16f4ecf29355a77a2bcf3c9f519b59a875c6919cec2e7a41f883553f127f807",
      "uv.lock": "818e60fbedee798145c4f228a35b30847bba0b5827a77aa8aaa0210407b69c9b"
    },
    "scope": "dependency-environment",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/development/contributions.md: dependency environment

Evidence for [the canonical document](../../development/contributions.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
