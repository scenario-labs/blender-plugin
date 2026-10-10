---
{
  "type": "Evidence",
  "id": "docs-mcp.render-form-trained-models",
  "title": "Trained models in render_form inspection",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "render-form-trained-models",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the inspection paragraph of Preparing Render Image and Render Video: render_commands.inspect returns trained_models with each Render Image slot's model ID, kind and strength rounded by trained_models.slot_scale (null without a strength control); render_commands.request and estimate_cost/generate for render lanes use generation.build_request, which writes these slots with trained_models.apply_to, so render quotes and generation include them, and a choice that cannot run returns its reason in errors. render_commands.inspect and request first call trained_defaults.apply_pending for the scene, which writes the selected credentials and project's saved Render Image default into a form without model_key or trained slots once it resolves, or leaves that form blocked with the reason; render_commands.configure records a named model_id as model_key before its inspection, so naming the shown model is an explicit choice the default no longer replaces. configure now also takes trained (render_image only): trained_offers.picks_from_list checks the shape and trained_models.checked_choice checks listed kinds, trained_routes.apply against the form's (new) model, explicit strengths only with a declared range and a selected connection, all before any change; replace_choice then writes the slots with write_slots, sets model_key, and [] clears them. Defaults are read, saved and cleared by model_defaults (topic docs-mcp.trained-models-mcp). Installed tests check the listed and empty inspection cases (test_trained_models), a Render Image default applied through render_form and configure naming the shown model or none (test_trained_section), and configure with trained: a stack written with ranges and the scope tag and sent by build_request, six refusals that leave the form unchanged, a composition and an empty list (test_mcp_trained_models). The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,264 tests (OK, 2 Windows-only skips) with ZIP sha256 d64765ad8f515f272d21c3fdb9b4f04645d43b053f4f86355d741915cb65e16c, whose 148 Python files match git archive of the reviewed implementation commit, including the 10 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality. Re-checked on 2026-10-12 after two review findings, with this paragraph's new sentences on configure: render_commands.inspect, request and configure without a named model_id run apply_pending through _apply_default, which logs a failure while writing instead of raising it, so a governed form reports its applying or unavailable reason from build_request (in errors from inspect, as a ScenarioError from estimate_cost); configure without model_id applies the default before it reads the form's model, validates the edits against the default's base and, while trained_defaults.blocking_reason is not empty, raises that reason without changing the form; a named model_id still records model_key and skips the step. Four new installed tests in test_trained_section cover these cases; three of them failed on the unfixed head and the named-model guard passed; the installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 then passed 1,855 tests (OK, 3 skips) with ZIP sha256 b2b27b19d82cf47339f8150817024018311dfe58efeb591bfcf0b79f46d30236, whose 189 Python files match the scenario/ sources of the fix commits. Only the docs/MCP.md, render_commands.py and test_trained_section.py fingerprints are refreshed; the other sources were not re-reviewed. Re-checked on 2026-10-12: the only change to test_trained_section.py adds an Image-form test of a governed form already showing the default's base, which no claim here depends on; only that fingerprint is refreshed.",
    "sources": {
      "docs/MCP.md": "4db0225d41694ad4b55bef05d65e35d72ae8cf10dcf531b133eb0ad1fb7be182",
      "scenario/blender/render_commands.py": "e6888cd27ae5ac6c9593bf61a2e167021f4173d7087059054440f770376c1c17",
      "scenario/blender/trained_models.py": "9b54ff883bc36fdecdd7ddb4e29669cee786722204ec611899d89b1f0a703ba5",
      "scenario/blender/generation.py": "339ce612dd6d2dc0fe05478d53f1742ed267f3363465ce4cac68ea4b011c1920",
      "scenario/mcp/tools_scenario.py": "9b0e2dd87ff708889636525124c4a1eb935a45e56983f9138872742717d067db",
      "tests/blender/test_trained_models.py": "247bc538aecd573d4de44c10006044f0adbf6270185babafca6ba377e0b0fe3d",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "tests/blender/test_trained_section.py": "cccd18467914ad3e62f00a7e7c302b08b34ceac96f7ded93be59d47c85d9800a",
      "tests/blender/test_mcp_trained_models.py": "19be55835046a01f521c9df0be18ee286f6d58ab1cf3a744209e2a54fcf8ea5a"
    }
  }
}
---

Evidence for [the canonical guide](../../MCP.md).
