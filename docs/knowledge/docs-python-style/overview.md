---
{
  "type": "Evidence",
  "id": "docs-python-style.overview",
  "title": "docs/PYTHON_STYLE.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/PYTHON_STYLE.md",
    "coverage": "inherited",
    "reviewed_at": "2026-10-13",
    "limits": "Whole-tree CI lint reviewed against the reusable lint workflow, its caller and the make lint target on 2026-10-13: the tree is Ruff-clean after #28's hand-fix and mechanical PRs, nested agent worktrees are Git-ignored and excluded in the Ruff configuration (a planted unformatted file there survived make format and an explicit-path run), and .git-blame-ignore-revs lists the mechanical commit. Other inherited guide sections retain their prior limits without a fresh claim-by-claim or live verification. Retired snapshot exclusions were removed from the reviewed Ruff configuration after their files moved entirely to Git history. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; complete secret detection and repository protection remain separate.",
    "sources": {
      ".github/workflows/ci.yml": "231efb391bdbb0c826eb61e1b5805bd7c4f4d31a02f832bd28a4b8b10ca26e87",
      ".github/workflows/python-lint.yml": "e3238c020a5a48ef3f7565d85de46074520d6f0ff87a9aaf39e5b7065df6a008",
      ".pre-commit-config.yaml": "680ea251ccacb8b228e41c104abec8d7400b732f7c4f21d9ee7c427b234fd7fd",
      ".python-version": "f7401ec58a777fe2a730f8805ab7f63ff80f064930c616b18efe3a475daf57fd",
      "pyproject.toml": "fbbdb3ed375ace12bb10f08a48300ea0cca0f28d1cfa2232647efa9adcb6d8a6",
      "Makefile": "4a176bab88c63563c69f4812073f76040f7c03cca0730dab42a563399c600f72",
      ".gitignore": "38babf3787024799e53b78e5717c1f731cf8dccd6073afff4a7bbc02d03a7f31",
      ".git-blame-ignore-revs": "85f3b69f23268bfec7af866520c5981ed8974295a40e76553dd3a8ed4e421ed1"
    },
    "scope": "overview",
    "base_revision": "fdcd91b832cffa79380cf14f1d2da10eed746829"
  }
}
---

# docs/PYTHON_STYLE.md: overview

Evidence for [the canonical document](../../PYTHON_STYLE.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
