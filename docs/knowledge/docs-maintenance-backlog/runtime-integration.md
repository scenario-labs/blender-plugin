---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.runtime-integration",
  "title": "docs/maintenance/backlog.md: runtime integration",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Agent source inspection of the listed files; no live service calls, native runtime rerun or human verification in this review.",
    "sources": {
      "scenario/blender/capture.py": "b8c2caae26103f45ea2bd619578360db3b464faf9f21a2938f033d630975016e",
      "scenario/blender/history.py": "c34d723e29b39fc88b3cd6ec88a188644dd2bb273a7ef2bad63d8f97e61d6df6",
      "scenario/blender/props.py": "0cac5c223860ed7e3709fda2a415ed1a7847c990d26d42ede0a0ce7def10ac21",
      "scenario/blender/registry.py": "a34fcb0110b5c991764df22d423546d9de3c949d3183b6dad1c5ca9e05123af2",
      "scenario/blender/runtime.py": "2afa6267f835569288ae6d1947af5410b05a0bbdcd3bbad985ff30a6dcb8a000",
      "scenario/core/api/catalog.py": "eeb58620545eb0438efc120fe46d7860f7df16e383f3a4b4c55b3282b7b17df9"
    },
    "scope": "runtime-integration",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/maintenance/backlog.md: runtime integration

Evidence for [the canonical document](../../maintenance/backlog.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
