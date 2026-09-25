---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.credentials",
  "title": "docs/architecture/runtime.md: credentials",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged.",
    "sources": {
      "scenario/core/config.py": "74a45b99fde47d741710dbf2a9d8051f2b31903f10ecae679d061340c62fb1be",
      "scenario/prefs.py": "a96da37fa23ed9ffb6be31c11cc6d519b15e3103555c84e7e14a60d2adcaf6bf",
      "tests/blender/test_credentials.py": "0767fbe1917c977631dc4243bfcb05dce97d5ed0c0b2c731b8ea4bfdb07e3b45",
      "tests/unit/test_config.py": "3d8ea8a6f0bcef70f0bb16146e794346cbbe7d2fc0f26aec1631b108cf6914f3"
    },
    "scope": "credentials",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/architecture/runtime.md: credentials

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
