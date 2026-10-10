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
    "limits": "Reviewed the sentence added to the local MCP bullet: list_models with the trained source returns trained model IDs, names, REST types, private flags, base names and composition concept IDs and strengths (trained_offers.describe_offer, no thumbnail URL, owner or project identity), and model_defaults returns and writes the saved defaults (model IDs and strengths) of the selected credentials and project. Both go only to the authenticated local MCP client; what the agent's own service does with them is outside this extension. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,266 tests (OK, 2 Windows-only skips) with ZIP sha256 e62f0acc496aef67a835b014532c94326220640c541d130fe5a36a4632efb9d6, whose 148 Python files match git archive of the reviewed fix commit, including the 12 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Re-checked on 2026-10-10 after the MCP fix commit (ensure_record, apply_picks, placement_error, _described and model_schema/_body_for): the new refusals carry fixed text naming input labels, positions, kinds and declared model types only, and list_models and model_defaults return the same fields; the claims above still hold. Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/PRIVACY.md": "3fca9ce9a80d241ef217c561d5daec586520f1da3b9e4177a2a1d5621ce283e1",
      "scenario/mcp/tools_scenario.py": "32962ae1546dd74f80da6a0e4c5ca05c5c403496dd2657341156dc88667825ba",
      "scenario/core/api/trained_offers.py": "863c3d82fa83b00fe097daf72240367482c4119d2d2f0203f8918dce2c34f1e3",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/core/jobs/model_defaults.py": "1e4fbf2f0cfb8de6cefd1a45ea82bbb0ecad9a1dd179f3a98b71519ca61dd93d",
      "tests/blender/test_mcp_trained_models.py": "9f959cfe352d90fe7fdd1e5606b5c925d043f0fdd02cfdda311b1fd4a1a07375",
      "tests/unit/test_trained_offers.py": "4ab4815ae411df1457d5adae24806983ccd2257b8ebc8dbc75eeb098980798f2",
      "scenario/blender/generation.py": "17c12bf4ee35dd3e0f15b5fdc9b0038d394330f601160ca1e8eb80b86df99a8b"
    }
  }
}
---

Evidence for [the canonical document](../../PRIVACY.md).
