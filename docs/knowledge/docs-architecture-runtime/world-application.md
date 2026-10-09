---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.world-application",
  "title": "docs/architecture/runtime.md: world application",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. The primitive's saved media-type to container binding, JPEG decoding and post-decode OpenEXR color space agreement check were reviewed; runtime.md's World claims cover them without format-specific detail beyond the saved World replacement sentence.",
    "sources": {
      "scenario/blender/world_application.py": "341b67665ec8be9201c3191559d47a31421aae5726bc2ea06b134f8245876895"
    },
    "scope": "world-application",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7"
  }
}
---

# docs/architecture/runtime.md: world application

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
