---
{
  "type": "Evidence",
  "id": "docs-mcp.sdk-cost-previews",
  "title": "SDK cost previews",
  "description": "Active credential-bound cost preview integration and its acceptance limits.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "sdk-cost-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "base_revision": "76b624d697f6a944fb53b831fd33b097ed95bfcd",
    "limits": "Source and synthetic SDK transport review covers active UI/MCP cost previews, exact Decimal/response retention, dryRun query placement, stale credential/form rejection, original-scene delivery including copied/deleted scenes, nested input snapshots and MCP main-thread preparation/delivery around off-thread network work. Installed-ZIP suites on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64 each pass all 349 tests, including the new estimate cases. No live/paid calls, durable submission, authoritative identity/project discovery, complete platform/input acceptance or human approval is claimed.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "0f9fb941bc72d2dab9f256186db600a30164ee56b0c5279cc736ff3e6a11ed29",
      "scenario/core/jobs/manager.py": "088ceef062935811ff282f628c0302792b370f27cf6b8557cc1f5547f314ecbd",
      "scenario/blender/generation.py": "c7449d4a9901f6a3ee6bc7956c7fb9e8000a5b5e023eceab37a8837bb2ed4826",
      "scenario/blender/handlers.py": "9826c9ff617d909b74a32c1da99be6e857a67949292c0a8341ff5b4ebb865ec8",
      "scenario/blender/runtime.py": "cf40830d2432dfaa210f6d264f984c72076fa9f24fdbfeaacb5fc33f1c95f822",
      "scenario/mcp/protocol.py": "f41a0283918d116a77888b4d018d0d353ba80162be8c75f029a67ad774fcd976",
      "scenario/mcp/tools_scenario.py": "f7e7ec94ef564ad77761cb33ae4b292a37e0f3f8d32cf759f0b30732ead9fb33",
      "tests/unit/test_sdk_catalog.py": "fa896966a7d37e16731d94ef76a203e952a1d2ed704705ba172c755449bac6e2",
      "tests/unit/test_catalog_delivery.py": "239e88efa293138a3b7ed5aa1a6d7ab31e4d0abf55f8a71035a556213e4c9348",
      "tests/unit/test_mcp_deferred.py": "f560070df327d3d1c348a727c12f076833e50057fb7020d92b2840fdda8e4093",
      "tests/blender/test_sdk_estimates.py": "69d58fc4c9cfd3d43b82d5fc71bc983b1e5ce695a0cdc98eb60dd7c0d7aa1ea4",
      "tests/blender/run_all.py": "d92ca29db0cf20316d75d80c4e7d5e69fa6eb9a6498ae2a6e858bf466fc9e35e"
    }
  }
}
---

# SDK cost previews

Evidence for [the canonical document](../../MCP.md).
