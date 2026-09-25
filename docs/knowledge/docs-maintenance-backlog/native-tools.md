---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.native-tools",
  "title": "docs/maintenance/backlog.md: native tools",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Agent source inspection of the listed files; no live service calls, native runtime rerun or human verification in this review.",
    "sources": {
      "tools/blender_env.py": "0e78f2a51edd2943567226537d8faed6170d41ba10ba84a663118b9b2c2251b8",
      "tools/test_blender.py": "fec317c68c24c49302b456a478e02a0a8352d29aa30c3e9e3cf173d47f0697cd"
    },
    "scope": "native-tools",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/maintenance/backlog.md: native tools

Evidence for [the canonical document](../../maintenance/backlog.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
