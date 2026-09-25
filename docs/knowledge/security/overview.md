---
{
  "type": "Evidence",
  "id": "security.overview",
  "title": "SECURITY.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "SECURITY.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-23",
    "limits": "Private reporting and supported-version policy; scope is not a claim that runtime hardening is complete. Repository private-vulnerability reporting was verified enabled through the GitHub API; Security-tab policy appearance requires merge.",
    "sources": {
      "scenario/blender/mcp_service.py": "63d3a6e36b0247d9529918957e4f92d08a48b704b28315017d2cf61914fb7ccf",
      "scenario/blender_manifest.toml": "b942bfc79b1ebecab7ae8f2ea16bac4a182d6a13d81dac3a23391dc2ffd16e0f",
      "scenario/core/config.py": "93b78f68c5da3c31e191fa3f1a08ac3fdffe8e3f1cac40a20bed4843672f28fe",
      "scenario/mcp/server.py": "d05a27729cd0835aedd023342713cb4b31107738f711026d24ab86f4052cd354",
      "scenario/mcp/tools_blender.py": "fce4b12492465b86691eede9cc6655220aab3087dcb2496a9600a0299abed520",
      "scenario/prefs.py": "24297fc14575f5e0c3a534516dc85961c28066aab0b0e00741247ed2e376d83b"
    },
    "scope": "overview",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# SECURITY.md: overview

Evidence for [the canonical document](../../../SECURITY.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
