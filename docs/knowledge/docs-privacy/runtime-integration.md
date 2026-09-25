---
{
  "type": "Evidence",
  "id": "docs-privacy.runtime-integration",
  "title": "docs/PRIVACY.md: runtime integration",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Discloses the active prototype and explicit credential source in this checkout, including known online-access and MCP quote-approval gaps. Separate replacement components are not active-runtime acceptance. No live service call or legal-policy audit; native synthetic preference-storage tests verify local persistence.",
    "sources": {
      "scenario/blender/generation.py": "8a3b2cc6b1992f3094e47e2ab5bd5af1f7babeb6dae86d7710ec91a1fd65895b",
      "scenario/blender/operators.py": "0cb4bb2c0566a7a30462ebaf158a8a954dcc9a14b305dc4a13e4cbc4655c6473",
      "scenario/blender/pump.py": "f3b5718c778bb3906f4d07a18a3a87e856812b1aea4a889b533124f9812140bb",
      "scenario/blender/registry.py": "a34fcb0110b5c991764df22d423546d9de3c949d3183b6dad1c5ca9e05123af2",
      "scenario/blender/runtime.py": "2afa6267f835569288ae6d1947af5410b05a0bbdcd3bbad985ff30a6dcb8a000",
      "scenario/core/api/assets.py": "f450202822d63f3caec36bb88c5e8c6aeb744e3a6ead66626578791a94b81f78",
      "scenario/core/api/client.py": "4473ecf5dbd7522efe358b99bafda0fd4fdd01c26a678e81fc82acd97bf9632d"
    },
    "scope": "runtime-integration",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/PRIVACY.md: runtime integration

Evidence for [the canonical document](../../PRIVACY.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
