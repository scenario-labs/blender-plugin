---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.credentials",
  "title": "docs/maintenance/backlog.md: credentials",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Agent source inspection of the listed files; no live service calls, native runtime rerun or human verification in this review. On 2026-10-10 the config.py and test_config.py fingerprints were refreshed after model MIME aliases joined the local result name table with a unit test; credential resolution and these claims are unchanged, and the review date is unchanged.",
    "sources": {
      "scenario/core/config.py": "933d9838304f903e2ab79fb60bbab76f999d12b76e9bd8a8525cd27c1f8ccee7"
    },
    "scope": "credentials",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/maintenance/backlog.md: credentials

Evidence for [the canonical document](../../maintenance/backlog.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
