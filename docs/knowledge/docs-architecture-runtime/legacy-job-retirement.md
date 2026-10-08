---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.legacy-job-retirement",
  "title": "docs/architecture/runtime.md: retirement of unscoped prototype job dispatch",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "legacy-job-retirement",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03b070b9cb663b63cf8a411f6126efb40d4c66d0",
    "limits": "Inspected removal of the native raw-client factory and prototype manager submission/resume/poll/download methods, preservation of read-only local records and explicit local media controls, rejection of unbound result application, and immediate prototype MCP snapshots. Shared SDK job and transfer implementations are unchanged. Regression source covers unchanged registry bytes, online/project transitions, late completions, authenticated local reads and shared deferred waits. No paid/live provider, desktop interaction, full retained-helper retirement or complete release acceptance is claimed. Exact candidate f4376ab6616e3dbfa59138416379fae9b58ed5663e2f6f53e226b6ac2b3b1fbb passes 1051 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with normal profiles unchanged; 3839 unit tests pass with the known SDK authentication expected failure.",
    "sources": {
      "scenario/core/jobs/manager.py": "688131a12cb5b7c8fde7d014ce2ceea131b17cd9dda279502e2aac4d9ea45707",
      "scenario/blender/runtime.py": "f85b53a9684831297fc07b6715d3286169c2713dc1116bbdb8220a979dcefe4f",
      "scenario/blender/pump.py": "aae6c6a454ef558d76ce5de90d08ced87f1f5904087d28f2d3ca49ed3bc1e11c",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/mcp/tools_scenario.py": "1d613605107ee7db59790faec37e8a3bd4ee8a014c38b00e0b44be20b67f12c3",
      "tests/unit/test_manager.py": "ef845dac3476da8ffc5ea78f152b0ed2c34214752a5c4227cb151766b55c78fe",
      "tests/unit/test_catalog_delivery.py": "a6fa18d0a7001a26d912e09d021abfed904399d4118ec7d256d55fc11492c011",
      "tests/blender/test_offline_runtime.py": "3429f261772abd43507d88a666ad9135a606c8927b20bf4e504c81c7d29c2c6e",
      "tests/blender/test_generation.py": "893b2601f6b694417878ad9d66a703fa6631f133090173b1a28687f135ae961a",
      "tests/blender/test_mcp_wait.py": "d6dd50e7b850e707bc8124665ecf415b84b51968c9ef02c4eb1fbffd4c2fad47",
      "tests/blender/test_mcp_contracts.py": "4c3bbbceed2a67cbeb81fba6a2f66dcfacb1f1d9bb5e9fe7ef0af88b582aa068",
      "tests/blender/test_model_generation.py": "0ea4f5ef5c1211f922d453df93b0ef98d886c19c20faea2bf477ff6c2ce57b52"
    }
  }
}
---

Evidence for [the canonical document](../../architecture/runtime.md).
