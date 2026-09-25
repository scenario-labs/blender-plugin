---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.uploads",
  "title": "docs/architecture/runtime.md: uploads",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged.",
    "sources": {
      "scenario/core/jobs/upload_sources.py": "76a578fa9dda550391e8c1f31959983b4e7b64cf4bb9a2dafca834e1b99ca9ff",
      "scenario/core/jobs/upload_store.py": "e53e44059fba806e5284f75327277fc7dcfceb7cd8a5f77e7a57696ce6372cf8",
      "scenario/core/jobs/upload_transfers.py": "eaf79e69f14dab7ff00a3a5217dd51a70aba04d36e67fb11b204131e25461259",
      "scenario/core/jobs/uploads.py": "73575da4b3f3589dead6a8b71d64feac2edcae789fb97f502b332fb5fe1789cc",
      "tests/blender/test_session_uploads.py": "de7a64d5c567c172da47b2c9e060bd14d2e1db5f4db896aec6258305501c2dab",
      "tests/blender/test_upload_commands.py": "496927b98c0774db28bac4da626f568bc147c9fc45f07da9e99a1aba0a0be9f1",
      "tests/blender/test_upload_store.py": "b5bdade91572d9d8a919fbe8dea2a2cb4587a3f53e7b48425e95af5e1cd20a41",
      "tests/blender/test_upload_transfers.py": "f6847d8595f363b66b00bcbc7d5634b5212221e7b8cda49e2eefd8eebfdd0b4e",
      "tests/unit/test_upload_commands.py": "5541ca299891a95ad0a41e4fe7261c74ba08a356261b68332517c20b7076fd76",
      "tests/unit/test_upload_inspection.py": "91a94ade8fbbb4f603273056b8db9b2bb8fbada3cbf910869b9e5b67a73044bd",
      "tests/unit/test_upload_store.py": "499172c31e93300bbe3e7b0ad870bdb9e27b2ee99163317ff1c04e0f48061a35",
      "tests/unit/test_upload_transfers.py": "0d26e96c55bb0c895220d0d0f64a4573067d9630ec0e9fc80525a8a126d77d97"
    },
    "scope": "uploads",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/architecture/runtime.md: uploads

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
