---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.blockout-runtime",
  "title": "Shared Blockout plan runtime",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "blockout-runtime",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "ea77f3a542be698301bd0a414579d4a9e40650bb",
    "limits": "Earlier scoped Design/Refine quote, submission, complete-text delivery and local-build evidence remains as documented in the canonical UI guide. Review fixes: guided invalid-plan refinement before quoting, reclaiming finished action handles while retaining uncertain jobs, and pruning deleted saved-plan destinations only after pending reads are drained. The exact b0bc4c291aa5d910beb53d34974526c74e5971d3462b326006cb521c697faeec package passes 746 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Synthetic Blender 5.1.2 desktop checks verify saved-plan cancellation, confirmation, native Undo/Redo, separate Build and viewport front-view/zoom input, with no further submission and an unchanged normal profile. No live provider, other OS/DPI desktop, Film or integrated release acceptance. Unchanged neighboring source fingerprints retain their earlier evidence.",
    "sources": {
      "scenario/blender/blockout_jobs.py": "d2ee582d3755a4e879012387303b60f344c8bcd2fbada345abe6b2196987ec92",
      "scenario/blender/blockout.py": "d5eb2efde4e0ff7f379c7b1d46222e85e9e88773f43af3db90828b530785ee7c",
      "scenario/blender/job_session.py": "7f40e24ae6dfecba75bb0353f4c6ce5e580677b1397bf679bfd048a0c2aee838",
      "scenario/blender/runtime.py": "cf3fb1d6bfd7ee1860086aecffb81ad6e4bb8d61596738038191c3e0c5b36df1",
      "scenario/blender/props.py": "f33955bbca26a36c8439ea3d57b2ef75110947ac8605cd21c2e903dac60d3bdb",
      "scenario/blender/panels.py": "dafe82fe2ece1fb90348116febef99079b96c9e0aa9e517dea3fed1d20d2ffde",
      "scenario/mcp/tools_scenario.py": "ff855eee9fd35166a0f4fd14349ffbb4eeb7903cd069984b64aba36a6f780953",
      "scenario/core/api/sdk_adapter.py": "6cc3758eebf05f066a0aa11ed4d5c6ec96fb87b72f02f3d609cfdd97b88b044e",
      "scenario/core/jobs/results.py": "ec817fa50b5ed82012233df0ede33266573368bc74b38d02aee30eba87ec775b",
      "tests/blender/test_blockout_jobs.py": "867fc53b29f6e252aa6cbef32073606ff1f515ce9caa20dae241b43635bb8e6c",
      "tests/blender/test_blockout.py": "ae28153eeed955e084d4933d570ca5645c1d743cdd72e2587bfd2e289733f1f4",
      "tests/blender/test_mcp_contracts.py": "403bf959d28a98156fd23951cc933a33494ab23380a9de8a2b7c171f8a86c530",
      "tests/blender/run_all.py": "1df5a5f3866696d891c784960f84920eb2ac1509b8a30d994642b6f9c2854814",
      "tests/unit/test_mcp_descriptions.py": "a04a7f7a3a7e13d3802448703b27fa93c1133519e453b05d56660a1f8c4bd656",
      "scenario/core/scene/blockout.py": "9e5fb64a78cc05085d94094d25581beb6109cdbd2625e65ce2ab6d8a702483ef",
      "tests/unit/test_blockout.py": "8e735f656c827a7ee665d9e63df3f56df3ec8f5344fe96dd350f8af905f0667e"
    }
  }
}
---

# Shared Blockout plan runtime

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
