---
{
  "type": "Evidence",
  "id": "docs-user-guide.sdk-connection-check",
  "title": "docs/USER_GUIDE.md: SDK connection check",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "sdk-connection-check",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed Test connection worker ownership, background completion delivery, selected credentials, cache preservation, stale-event rejection and status icons against the current connection paths. Reviewed sanitized adapter status text: HTTP 401 names the key and secret; HTTP 403 names the key and secret, and names the Project ID only when that request carried the override (unscoped discovery never does); HTTP 429 asks to retry later; other statuses keep the generic HTTP text. Messages are fixed strings without response bodies, URLs, credentials or IDs. Preferences wraps the account label at 70 characters and the sidebar wraps catalog errors at 36 characters. 3938 offline unit tests pass with the known SDK authentication xfail. Exact ZIP a5e87b893edbf6d73c71279f6769e070e7fc836186bc763c0990fb1d632ca30f passes 1150 installed tests (2 Windows-only skips) on Blender 5.1.2 macOS arm64; an offline capture of that ZIP showed the wrapped 403 Project ID message in Preferences. Blender 5.0.1/5.2.1 runs, desktop input/focus, the sidebar error capture, live 401/403/429 responses, paid execution and account/project identity discovery are not claimed. Reported live checks returned 403 for both a wrong secret and a nonexistent Project ID, so 403 guidance names both causes; this review did not repeat them. Other guide topics retain their independent evidence limits.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/api/sdk_adapter.py": "667adf4e93fe645abaf78790a4c99bad56467f7a366a24169d50e99b86ed7d94",
      "scenario/core/jobs/manager.py": "688131a12cb5b7c8fde7d014ce2ceea131b17cd9dda279502e2aac4d9ea45707",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/blender/operators.py": "8fb3a35beb010e81f4d4eaecf22688d8baf051ad88cdf2def50664e0da01a103",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/blender/panels.py": "c63ff026a228cc723e5ebf988dee194725a9c0caff75b65756355222ab66ac27",
      "scenario/prefs.py": "569ef8524cb0ba9e7d8f5b46582d4903b05d96a7cbc6cf1f2b3216be23c4ba96",
      "tests/unit/test_sdk_adapter.py": "7a50dec35937444822a78dd98aa62a067af9b21087943a1f473282849dc86778",
      "tests/unit/test_sdk_connection.py": "3bdcfbbffce950710bf67af4cdd17b54839e40cc9ddfef8f929d9ca79b0e395e",
      "tests/blender/test_sdk_connection.py": "1953f5c93f1c9d02dad49f6d4e8a5d377c720a4aaa7589e7e1fa8aec73f490e2",
      "tests/blender/run_all.py": "0c167da4d582bd9eda230638ec4259ba22357c857ffd240b58485cbdd07a26a1"
    }
  }
}
---

Evidence for [the canonical document](../../USER_GUIDE.md).
