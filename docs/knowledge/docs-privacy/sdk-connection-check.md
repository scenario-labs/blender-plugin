---
{
  "type": "Evidence",
  "id": "docs-privacy.sdk-connection-check",
  "title": "docs/PRIVACY.md: SDK connection check",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "sdk-connection-check",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Reviewed the active asynchronous Test connection path using one fresh SDK model page, selected credentials, cache preservation, safe errors and stale-event rejection. Offline unit contracts and exact packaged native suites pass on macOS arm64 with Blender 5.0.1, 5.1.2 and 5.2.1. No live service, paid execution, account/project identity discovery or new UI layout/input acceptance is claimed. Other guide topics retain their independent evidence limits.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "73341abb8a32e91dd10c3fe272fb9f49922b648bfef7103b7938d3a69bbefc82",
      "scenario/core/api/sdk_adapter.py": "c6e89405e668a38a0d68237c9cab183cfcb8ef289fc8396595979dbf44c71b80",
      "scenario/core/jobs/manager.py": "88a95bd3e7a02fef36c86ef45cd1f599e8b141313197b84f0daeb8825db558d8",
      "scenario/blender/runtime.py": "680ef941080963ed55b185399f46ec045bdaf9601dc75cbe9bf7766f00384b50",
      "scenario/blender/operators.py": "ab29e70dabd96307f31df7026f07c4abb1e85e83eff42a35b78542ddaac35076",
      "scenario/blender/handlers.py": "5e669201d98a69d49a0a4f6bb4f1bec0c8325efce5ef6eb2460dc47d0d2aee24",
      "tests/unit/test_sdk_connection.py": "0e0998d5dc3fd489b1f6de81605b8a0ce4efd0c06f47b913d0cb750fa0996f62",
      "tests/blender/test_sdk_connection.py": "4c2c069e841c2c09559b6138d565a55632cbb9e4a5b3cc68b2b925082ceb9191",
      "tests/blender/run_all.py": "3473dde987385d7d6037877c334aa5ceac3956dd2b1185edec18d157715127da"
    }
  }
}
---

Evidence for [the canonical document](../../PRIVACY.md).
