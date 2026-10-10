---
{
  "type": "Evidence",
  "id": "docs-job-storage.trained-defaults-forms",
  "title": "Native forms using the lane-defaults owner",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "trained-defaults-forms",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the paragraph replacing the earlier statement that no UI control used the owner: trained_defaults.load reads each Image and Render Image lane through runtime.ensure_model_defaults once per owner context_id into RuntimeState.trained_defaults, which trained_defaults.cached and view read without opening the owner (drawing never calls ensure_model_defaults); save and clear go through runtime.save_model_default and clear_model_default with the context_id and revision drawn on the Save and Clear buttons, refuse an empty context or negative revision before any write, and reload the cache after any refusal (a stale revision, a retired owner, another selection or an unreadable row); selection_default writes only stack or composition defaults with rounded strengths for a choice that runs; a form without model_key or slots takes its lane default once resolve checks the base description, the form's own model list, the trained list and trained_routes.apply, and is otherwise blocked without a base-model fallback; the cache is read once per context_id and again only through load(force=True) after a refused write, so a default another Blender session saves later is read after the selection changes or a write is refused; StoreError rows are reported per lane and the database bytes stay unchanged (installed test). render_commands.inspect and request call apply_pending for the Render Image form first. Re-reviewed on 2026-10-10 after save was split: save now passes selection_default to store, which runs the same _write and apply_pending; local MCP model_defaults uses this module (topic docs-job-storage.trained-defaults-mcp); the added explicit_default, lane_summary and trained_models MCP helpers change no form path. For this re-review, the installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,264 tests (OK, 2 Windows-only skips) with ZIP sha256 d64765ad8f515f272d21c3fdb9b4f04645d43b053f4f86355d741915cb65e16c, whose 148 Python files match git archive of the reviewed implementation commit, including the 10 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). The earlier review cited the installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9, which passed 1,254 tests (OK, 2 Windows-only skips) with ZIP sha256 5d94b5a727a8b20cf3640b15b1c4446053d79a75905fc79b1f282a84b119298c, whose 148 Python files match git archive of the reviewed fix commit, including the 21 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). The update probe with a candidate-derived 0.0.0 predecessor on the same ZIP passed with model_defaults_preserved and trained_selection_preserved true after update and restart; no persisted property or store schema changed. Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/blender/trained_section.py": "e4498d61dc304586bcfb4f6b8e487fecb9b18572fcc08587f38560637a4615b5",
      "scenario/blender/trained_models.py": "9b54ff883bc36fdecdd7ddb4e29669cee786722204ec611899d89b1f0a703ba5",
      "scenario/blender/runtime.py": "0cb590b37bf3593496cd09bb7c9167fab481ad3b49a211a828f1a3677c7368b4",
      "scenario/core/jobs/model_defaults.py": "1e4fbf2f0cfb8de6cefd1a45ea82bbb0ecad9a1dd179f3a98b71519ca61dd93d",
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "tests/blender/test_trained_section.py": "cccd18467914ad3e62f00a7e7c302b08b34ceac96f7ded93be59d47c85d9800a"
    }
  }
}
---

Evidence for [the runtime owner](../../JOB_STORAGE.md#runtime-owner).
