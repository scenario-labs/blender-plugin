---
{
  "type": "Evidence",
  "id": "docs-privacy.credentials",
  "title": "docs/PRIVACY.md: credentials",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Discloses the active prototype and explicit credential source in this checkout, including known online-access and MCP quote-approval gaps. Separate replacement components are not active-runtime acceptance. No live service call or legal-policy audit; native synthetic preference-storage tests verify local persistence.",
    "sources": {
      "scenario/core/config.py": "74a45b99fde47d741710dbf2a9d8051f2b31903f10ecae679d061340c62fb1be",
      "scenario/prefs.py": "bfd966d4a6dab2a8505caa3e9ed58d71b71d57b29b673feb5344ad6b8ed72e92",
      "tests/blender/test_credentials.py": "0767fbe1917c977631dc4243bfcb05dce97d5ed0c0b2c731b8ea4bfdb07e3b45"
    },
    "scope": "credentials",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/PRIVACY.md: credentials

Evidence for [the canonical document](../../PRIVACY.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
