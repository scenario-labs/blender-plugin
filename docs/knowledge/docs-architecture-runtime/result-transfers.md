---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.result-transfers",
  "title": "docs/architecture/runtime.md: result transfers",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged.",
    "sources": {
      "scenario/core/jobs/results.py": "6f8735b1fe64f0607ae63c4a5cb43c443904730ede7a2466ceb6439a425d93a2",
      "scenario/core/jobs/transfers.py": "549e02649dab7061492a5bb1100a836daf1112972a9ad01c2c0d39facb6ac098",
      "tests/blender/test_result_commands.py": "bcb919c9a8dfcd3498959492b5bb49a3f1395b6923282f38182cc9b12c68089e",
      "tests/blender/test_session_results.py": "fed6c554fe817c6d455d6e9a00a0e142d18366b285662448b1e8d453d1ee2fd6",
      "tests/unit/test_result_commands.py": "3bcba6d1b719ad3016fd5a68e0b740ff5d7eaba1924d59700f0e6d6adbec8009",
      "tests/unit/test_result_manifest.py": "e718f316b9f33faefdae53d59bf04c80b48645d52f3dd0bc80a2beae426e5d67"
    },
    "scope": "result-transfers",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/architecture/runtime.md: result transfers

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
