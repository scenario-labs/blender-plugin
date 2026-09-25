---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.fixture-recording",
  "title": "docs/SDK_ADOPTION.md: fixture recording",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "This pass reconciled upload staging, signed-part transfer, durable commands and optional JobSession forwarding with their implementation and tests. Existing active SDK catalog evidence is retained; other component claims retain their prior coverage limits. No active UI/MCP upload wiring, production storage policy, source cleanup, live service, paid-flow or authoritative account/project discovery acceptance is claimed. Single-page model reads and development fixture recorder mapping reviewed against the pinned SDK 2.1.0 artifact and offline request/failure contracts. No live fixture recording or media-rights acceptance is claimed. Exact packaged Blender 5.0.1 macOS arm64 baseline passed, including the new single-page SDK contract; broader hosted platform checks are separate.",
    "sources": {
      "tests/unit/test_fixture_hygiene.py": "8e97a06f5805289a73ec456f8ccc536dd233372d5736c817eebb6c6253f97492",
      "tests/unit/test_fixture_recording.py": "71d3242c85f842db704df775a07ae1d3c4ced5273fc46d2510249d404acfe4cd",
      "tools/record_fixtures.py": "8a8afcee21fe4ab44be34186d22ed7a825167e6461231d29846bfca4d71840f2"
    },
    "scope": "fixture-recording",
    "base_revision": "e013a26d7208f472b0d5d6fee1534763e2632f22"
  }
}
---

# docs/SDK_ADOPTION.md: fixture recording

Evidence for [the canonical document](../../SDK_ADOPTION.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
