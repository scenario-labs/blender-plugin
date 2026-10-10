---
{
  "type": "Evidence",
  "id": "docs-development-validation.schema-10-update-state",
  "title": "Schema 10 state, real predecessor code and its refusal across native updates",
  "description": "Store schema evidence, schema 10 seeding, previous-ZIP test predecessors and predecessor reopen.",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "schema-10-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the package probe's store_schema reports, schema 10 seeding before update or after the post-update upgrade, its restart checks, the runner's archive schema parsing (a package without a shared store now fails with a clear ValueError), the --previous-zip --test-predecessor mode and the predecessor reopen step: a factory-settings Blender process imports only the predecessor ZIP's core storage under a private package name, must get its unsupported-format StoreError, and the runner compares every file in the store directory before and after. On macOS arm64 Blender 5.1.2 a predecessor built from b57c398f (ZIP sha256 18b5dab6a335f9e3390a9f0982c2d97fe6a698fd5717d6729bbecd3b4833f418, schema 9) was upgraded through the native updater to a candidate built from this change (ZIP sha256 fb09c863b74aea68daeee91e263f439c89a71f82e9baed4a9cff8b067288c092, schema 10): all six prior jobs, the other scope, uploads, mesh and Film bindings, local claims, workflow references and scene survived update and offline restart, the schema 10 state written after the upgrade survived restart, and the b57c398f code refused the upgraded store with its bytes unchanged. A candidate-derived predecessor run with the same candidate also passed with schema 10 seeded before update and no reopen step. Both predecessors are synthetic 0.0.0 version metadata, not published release pairs. Unit tests exercise the reopen mechanics with the current code relabelled as schema 9, not the b57c398f code. Blender 5.0, 5.2, Linux and Windows were not run for this change.",
    "sources": {
      "tests/blender/package_update.py": "55924e344010e52cc51dbe1de73cb96a8390e1835964e046057b0d06512e7e07",
      "tests/blender/predecessor_store.py": "1535147e9cc3cd71ddee257f48a1c6dfa19aeb496eb56eddb056af1748674562",
      "tools/test_repository_update.py": "83c5079a86757a7c9802f957450ac03c391793f0d5ce69993c88553f532b44bd",
      "tests/unit/test_repository_update_runner.py": "2dce38231c65a53e481322a9f0158731280a3735999a0be81cd46dfdfe33ce7a",
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6"
    }
  }
}
---

# Schema 10 state and real predecessor code across native updates

Evidence for [the canonical document](../../development/validation.md).
