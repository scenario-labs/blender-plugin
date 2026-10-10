---
{
  "type": "Evidence",
  "id": "docs-known-limitations.credentials",
  "title": "docs/KNOWN_LIMITATIONS.md: credentials",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Agent source inspection of the listed files; no live service calls, native runtime rerun or human verification in this review. Legacy follow-up disposition reconciled with current credential, prompt, model-loading, audio and lane source. Public issue scopes/types and project Priority/Effort were read back after triage; this records tracking, not implementation or live/native acceptance. On 2026-10-10 the config.py and test_config.py fingerprints were refreshed after model MIME aliases joined the local result name table with a unit test; credential resolution and these claims are unchanged, and the review date is unchanged.",
    "sources": {
      "scenario/core/config.py": "933d9838304f903e2ab79fb60bbab76f999d12b76e9bd8a8525cd27c1f8ccee7"
    },
    "scope": "credentials",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/KNOWN_LIMITATIONS.md: credentials

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
