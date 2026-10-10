---
{
  "type": "Evidence",
  "id": "docs-job-storage.trained-defaults-mcp",
  "title": "Trained-model defaults through local MCP",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "trained-defaults-mcp",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Local MCP model_defaults paragraph: tools_scenario.model_defaults validates action, lane, context_id and expected_revision; get returns trained_defaults.load's owner context_id and lane_summary per lane (revision, model_defaults.describe default, resolve label and availability, waiting or unavailable text, parameters built with trained_routes.apply, error for an unreadable row that is left in place); set turns trained_offers.picks_from_list picks into trained_defaults.explicit_default (listed kinds choose stack or composition, a composition strength is refused, TrainedModelDefault validates, then resolve(read=True) refuses reasons and waiting) and writes through trained_defaults.store, the _write path the native Save uses with runtime.save_model_default's context check; clear uses trained_defaults.clear. Installed tests cover get, set with no price request, the governed Image form taking the default and its parameters pricing the form's payload, a stale revision, refused choices, another project's isolation with a foreign context refused, clear, and a composition default applied to Render Image. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,264 tests (OK, 2 Windows-only skips) with ZIP sha256 d64765ad8f515f272d21c3fdb9b4f04645d43b053f4f86355d741915cb65e16c, whose 148 Python files match git archive of the reviewed implementation commit, including the 10 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/JOB_STORAGE.md": "d10291adaac96f6d2c0e05b7c312269e498a5a2b75292fbd562a510a2504dc55",
      "scenario/mcp/tools_scenario.py": "9b0e2dd87ff708889636525124c4a1eb935a45e56983f9138872742717d067db",
      "scenario/blender/trained_defaults.py": "98a3d513af1100b9fc231da123b785e354e306f683e89f82e0af7fc0cceabe97",
      "scenario/blender/runtime.py": "0cb590b37bf3593496cd09bb7c9167fab481ad3b49a211a828f1a3677c7368b4",
      "scenario/core/jobs/model_defaults.py": "1e4fbf2f0cfb8de6cefd1a45ea82bbb0ecad9a1dd179f3a98b71519ca61dd93d",
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "tests/blender/test_mcp_trained_models.py": "19be55835046a01f521c9df0be18ee286f6d58ab1cf3a744209e2a54fcf8ea5a"
    }
  }
}
---

Evidence for [the runtime owner](../../JOB_STORAGE.md#runtime-owner).
