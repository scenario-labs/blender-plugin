---
{
  "type": "Evidence",
  "id": "docs-job-storage.trained-default-owner",
  "title": "Runtime owner of per-scope trained-model lane defaults",
  "description": "ModelDefaults over the selected job store, its retirement, context token and JSON boundary.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "trained-default-owner",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ModelDefaults: it accepts only a JobStore and takes its scope from it; reads pass through to trained_default and trained_defaults without writing or falling back; save requires a TrainedModelDefault and clear a lane, both with a keyword expected revision checked by the store; retire takes the same lock as every call, so it waits for a running call and then every read and write raises DefaultsRetired, a StoreConflict; context_id is an in-memory uuid4 token. Reviewed runtime ensure_model_defaults (binds to ensure_job_store and replaces an inactive or different-scope owner), save_model_default and clear_model_default (refuse a context token from another owner with ScenarioError), and retirement in sync_catalog_context and RuntimeState.reset. Reviewed parse_default (exact route/base_model_id/picks keys, picks as a list or tuple of at most 16 dicts with model_id and an optional numeric scale, booleans, strings, overflow and non-finite values refused) and describe (lane, revision and default only). Unit tests cover isolation through open_credential_store by credential pair, project override and team with no fallback, read-only reads, explicit writes and revision rules, racing owners, retirement waiting for a blocked write, damaged rows and an unknown schema version preserved byte for byte, a replaced symlinked database, POSIX permission bits, and the JSON boundary for every route. Installed-ZIP suite on Blender 5.1.2, Python 3.13.9, macOS 27.0.1 arm64: 1213 tests OK (2 Windows-only skips), including the seven ModelDefaultsRuntimeTests; ZIP sha256 0d675ed1734d9080f7845e678df1c741b2151e3ffc0be36efc59d6258f9db6a1, whose scenario sources match git archive of the reviewed head. No UI control, MCP tool, route derivation, schema recheck or quote uses the owner yet; nothing here establishes trained-model acceptance for #97. Blender 5.0, 5.2, Linux and Windows were not run for this change.",
    "sources": {
      "scenario/core/jobs/model_defaults.py": "1e4fbf2f0cfb8de6cefd1a45ea82bbb0ecad9a1dd179f3a98b71519ca61dd93d",
      "scenario/blender/runtime.py": "4389630c31be63af3ca76f146712d3d4ca197550ae04899bd1e80c394bde637a",
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "tests/unit/test_model_defaults.py": "ff6cd13190c1c0664a5e09b4c808bb224e7005222607f9a3377b8e12d74b1690",
      "tests/blender/test_model_defaults.py": "d9ee6a5c75418fe71f27c37c894967f3a0fc6d294debdfbf330bb0ccaa8029aa"
    }
  }
}
---

# Runtime owner of per-scope trained-model lane defaults

Evidence for [the canonical document](../../JOB_STORAGE.md).
