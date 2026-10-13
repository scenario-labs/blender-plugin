---
{
  "type": "Evidence",
  "id": "docs-development-contributions.dependency-environment",
  "title": "docs/development/contributions.md: dependency environment",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/contributions.md",
    "coverage": "policy",
    "reviewed_at": "2026-10-13",
    "limits": "Canonical contribution policy, including inspected Actions-only Dependabot configuration and commit-title compatibility; configuration does not prove live update delivery or administrative action-pin enforcement. Inspected the actions-pinned house-rule implementation, CLI and failure tests; this scoped offline convention check does not establish general YAML validity, release tag provenance, other house rules, REUSE coverage or administrative settings. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; full-tree prototype normalization, complete secret detection and repository protection remain separate. Strict link workflow, canonical Markdown inventory, explicit authentication exceptions and scoped failure reporting reviewed with offline tests and a local network scan; hosted PR rejection and scheduled issue delivery remain separate acceptance. 2026-10-13: re-reviewed the GitHub Actions update section after .github/dependabot.yml gained a seven-day cooldown, matching the scenario-labs/skills configuration, and after the maintainer turned on required full-SHA pinning in the repository's Actions settings. The PR author read it back with `gh api repos/scenario-labs/blender-plugin/actions/permissions` (allowed_actions all, sha_pinning_required true), and Pages run 38419176170 on main passed with the setting on; a reviewer can re-run both checks. pyproject.toml and uv.lock were not re-reviewed.",
    "sources": {
      ".github/dependabot.yml": "e9e9d0d08cc7300deb06b90a19116dd21a426dbe7b639419517444347dd31204",
      "pyproject.toml": "d16f4ecf29355a77a2bcf3c9f519b59a875c6919cec2e7a41f883553f127f807",
      "uv.lock": "818e60fbedee798145c4f228a35b30847bba0b5827a77aa8aaa0210407b69c9b"
    },
    "scope": "dependency-environment",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a"
  }
}
---

# docs/development/contributions.md: dependency environment

Evidence for [the canonical document](../../development/contributions.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
