---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.runtime-integration",
  "title": "docs/architecture/runtime.md: runtime integration",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged.",
    "sources": {
      "scenario/blender/generation.py": "68958e267939eeb096d1e682252ffc0f88a1a944591495a55436d01382f77c8d",
      "scenario/blender/handlers.py": "ec2e79cb3da360c296d2a5abfb9e5120a8f78637a2e1940ea4661250464ef965",
      "scenario/blender/pump.py": "c2d3f42c15ef7c01abec6cb7e67b95b9c8085bf9b66aced9f00dfaa2f0a7f599",
      "scenario/blender/registry.py": "a34fcb0110b5c991764df22d423546d9de3c949d3183b6dad1c5ca9e05123af2",
      "scenario/blender/runtime.py": "e2aea444fd9ed8568038d709d3e0948a411dd26ba94994bb09efb55a0a2c7e31",
      "tests/blender/test_generation.py": "5c95b7409d2b20c0a8ce10498ad613dcf8fbd2bd9ab613b541e04754060ee866"
    },
    "scope": "runtime-integration",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/architecture/runtime.md: runtime integration

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
