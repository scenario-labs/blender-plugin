---
{
  "type": "Evidence",
  "id": "docs-privacy.local-mcp",
  "title": "docs/PRIVACY.md: local mcp",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Discloses the active prototype and explicit credential source in this checkout, including known online-access and MCP quote-approval gaps. Separate replacement components are not active-runtime acceptance. No live service call or legal-policy audit; native synthetic preference-storage tests verify local persistence.",
    "sources": {
      "docs/MCP.md": "fb6f2c0a82536d3d1af3a9a7787df2a67b7ebe7fb5eb66f7462d737c48f71f64",
      "scenario/blender/mcp_service.py": "ec45907c26301d5c0c2e48fe2eab09136cd52aadb00c6be5401d23ec7d868715",
      "scenario/mcp/server.py": "e201d006e5189f32742db38c3f2b00879fbcc1b71b665436b45a0930ff696cd0",
      "scenario/mcp/tools_scenario.py": "66e90694c9bc89878cec3ed2c133ac017492c9ebec866e1c850c07baf4b29543"
    },
    "scope": "local-mcp",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/PRIVACY.md: local mcp

Evidence for [the canonical document](../../PRIVACY.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
