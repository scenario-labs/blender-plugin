---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-history",
  "title": "SDK cloud history",
  "description": "Credential-bound UI and MCP cloud history reads and their remaining boundaries.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "sdk-history",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Source and offline SDK transport review covers single-page job listing, selected credentials/project serialization, bounded per-read prompt resolution, request/credential delivery guards, failed-refresh preservation, cursor cycles and empty-page/explicit-retry MCP behavior. No live service calls, paid operations, durable recovery, full prompt downloads, project-selection UI or history-result application acceptance is claimed. Final installed-ZIP suites on macOS arm64 pass 351 tests each on Blender 5.0.1, 5.1.2 and 5.2.1; this does not establish other platforms or full native interaction acceptance.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "82f2a780e55d0b464af3797b4cb7b916f0586603de63d238255ac3b56378b7bb",
      "scenario/core/api/sdk_catalog.py": "06f9f1d5158f4da603aaecb41f1252ab31aca2a918a6f17438ee6ce05693021e",
      "scenario/core/jobs/manager.py": "a69011bfd2a791a4d7aa9cb0d9e054c8f6eb27128a38aad22c03a66b0e55b840",
      "scenario/blender/history.py": "196f6984ded9803db82a931d3f1eea0e0d1b4aae918692a4d5e33e22c60ac8c1",
      "scenario/blender/runtime.py": "1b9746a7c579003a16b40b7c20dd23a6497726a8569b60f1df8764afebec4a25",
      "scenario/mcp/tools_scenario.py": "3d9f9e09c1837fb2f5f21052f674b48143530f9bd28fa971570243af98ec3de8",
      "tests/unit/test_sdk_history.py": "6f90cb89c217c897cfa7e2af647148175fa4fb00249a9f5a1af1aebe44e83d49",
      "tests/blender/test_sdk_history.py": "b9645d15035f44c0f1b8279c5c0f0c5d395689a01e1ddbd4cb4dc21aed13985a",
      "tests/blender/test_history.py": "7376399e5f6d1bb02b5ef051adb6df295d0af2d988c601fd74119a24ca69f134",
      "tests/blender/run_all.py": "2d79cd5df9446baa7e9d8b7fde812b07af5f7762ffa2c27373b71170b41766a0"
    }
  }
}
---

# SDK cloud history

Evidence for [the canonical document](../../SDK_ADOPTION.md).
