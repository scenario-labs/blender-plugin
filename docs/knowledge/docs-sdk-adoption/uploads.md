---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.uploads",
  "title": "docs/SDK_ADOPTION.md: uploads",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed.",
    "sources": {
      "scenario/core/jobs/upload_sources.py": "d75cd9ced1c578957a587c98526f1522bdbc91e6ce2dba62be099d68ea086623",
      "scenario/core/jobs/upload_transfers.py": "eaf79e69f14dab7ff00a3a5217dd51a70aba04d36e67fb11b204131e25461259",
      "scenario/core/jobs/uploads.py": "73575da4b3f3589dead6a8b71d64feac2edcae789fb97f502b332fb5fe1789cc",
      "tests/blender/test_session_uploads.py": "de7a64d5c567c172da47b2c9e060bd14d2e1db5f4db896aec6258305501c2dab",
      "tests/unit/test_upload_commands.py": "5541ca299891a95ad0a41e4fe7261c74ba08a356261b68332517c20b7076fd76",
      "tests/unit/test_upload_sources.py": "f3fdf69efd7426b53d29b2e60716bd2bcb582e6e1b48e79a11365356ee3c7c03",
      "tests/unit/test_upload_transfers.py": "0d26e96c55bb0c895220d0d0f64a4573067d9630ec0e9fc80525a8a126d77d97"
    },
    "scope": "uploads",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/SDK_ADOPTION.md: uploads

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
