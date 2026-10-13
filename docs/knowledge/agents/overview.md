---
{
  "type": "Evidence",
  "id": "agents.overview",
  "title": "AGENTS.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "AGENTS.md",
    "coverage": "policy",
    "reviewed_at": "2026-10-13",
    "limits": "Canonical instructions consolidated from the existing rulebook; normative requirements do not imply runtime acceptance. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; complete secret detection and repository protection remain separate. Validation rule re-reviewed on 2026-10-13 for whole-tree Ruff checks (make lint) after #28.",
    "sources": {
      ".codex/config.toml": "3ce4a01cd0ed404ad5ceb8d1b4c25e0e10bc6339ab1d94fd9936f8543c1b87f2",
      ".pre-commit-config.yaml": "680ea251ccacb8b228e41c104abec8d7400b732f7c4f21d9ee7c427b234fd7fd",
      "CONTRIBUTING.md": "ef691e96e2c3c057fbd3677aaab9fe505d40752e026c84f827c5d188c5ace48c",
      "Makefile": "4a176bab88c63563c69f4812073f76040f7c03cca0730dab42a563399c600f72",
      "scripts/agents/validate-skills.py": "82822cf1ed96c67c2b5d25e9d666171b37dc071427dd84ceda096e70697c7f3f",
      ".github/workflows/python-lint.yml": "e3238c020a5a48ef3f7565d85de46074520d6f0ff87a9aaf39e5b7065df6a008"
    },
    "scope": "overview",
    "base_revision": "fdcd91b832cffa79380cf14f1d2da10eed746829"
  }
}
---

# AGENTS.md: overview

Evidence for [the canonical document](../../../AGENTS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
