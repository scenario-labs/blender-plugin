---
{
  "type": "Evidence",
  "id": "docs-privacy.trained-models-mcp",
  "title": "Trained models and defaults visible to local MCP agents",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "trained-models-mcp",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the sentence added to the local MCP bullet: list_models with the trained source returns trained model IDs, names, REST types, private flags, base names and composition concept IDs and strengths (trained_offers.describe_offer, no thumbnail URL, owner or project identity), and model_defaults returns and writes the saved defaults (model IDs and strengths) of the selected credentials and project. Both go only to the authenticated local MCP client; what the agent's own service does with them is outside this extension. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,264 tests (OK, 2 Windows-only skips) with ZIP sha256 d64765ad8f515f272d21c3fdb9b4f04645d43b053f4f86355d741915cb65e16c, whose 148 Python files match git archive of the reviewed implementation commit, including the 10 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/PRIVACY.md": "3fca9ce9a80d241ef217c561d5daec586520f1da3b9e4177a2a1d5621ce283e1",
      "scenario/mcp/tools_scenario.py": "9b0e2dd87ff708889636525124c4a1eb935a45e56983f9138872742717d067db",
      "scenario/core/api/trained_offers.py": "71d3baf15c1e92212f159e31a432d20e2e8b2a0228c126df6e0b0c072952c4d0",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/core/jobs/model_defaults.py": "1e4fbf2f0cfb8de6cefd1a45ea82bbb0ecad9a1dd179f3a98b71519ca61dd93d",
      "tests/blender/test_mcp_trained_models.py": "19be55835046a01f521c9df0be18ee286f6d58ab1cf3a744209e2a54fcf8ea5a",
      "tests/unit/test_trained_offers.py": "9ee27b6ef294f1564778a1d14db0d86de3673db3ce64ed9da7a844221286bc87"
    }
  }
}
---

Evidence for [the canonical document](../../PRIVACY.md).
