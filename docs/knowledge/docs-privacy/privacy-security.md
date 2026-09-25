---
{
  "type": "Evidence",
  "id": "docs-privacy.privacy-security",
  "title": "docs/PRIVACY.md: privacy security",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Discloses the active prototype and explicit credential source in this checkout, including known online-access and MCP quote-approval gaps. Separate replacement components are not active-runtime acceptance. No live service call or legal-policy audit; native synthetic preference-storage tests verify local persistence.",
    "sources": {
      "tests/unit/test_privacy_docs.py": "d9f3ee2f403400da1758381f4ec0d3a643d83d189190f6c3201a5b3c60328526"
    },
    "scope": "privacy-security",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/PRIVACY.md: privacy security

Evidence for [the canonical document](../../PRIVACY.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
