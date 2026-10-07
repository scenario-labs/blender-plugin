---
{
  "type": "Evidence",
  "id": "docs-ui-style.shared-history-recovery",
  "title": "Scoped saved jobs in cloud history",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "shared-history-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "ea77f3a542be698301bd0a414579d4a9e40650bb",
    "limits": "Scoped history lookup and explicit saved-result recovery routing. The display uses a saved-ID snapshot from explicit reads plus live shared-job views; drawing performs no job database reads. Native/MCP commands continue to inspect current scoped storage. Storage failures disable row actions until a successful read, and credential changes clear the snapshot. Exact ZIP 27ebeece6da712d7b6fd50a8047736df8351e501679b1a4ad1503b62f82e7ac5 passes 751 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, including repeated-redraw, late-acknowledgement and failure/retry regressions. The canonical guide preserves preceding-artifact desktop/screenshot evidence; fresh desktop input on the changed artifact remains unverified. Unchanged source fingerprints retain their earlier review. No arbitrary-cloud-job adoption, prototype migration, live/paid provider, other OS/DPI desktop or integrated release acceptance.",
    "sources": {
      "scenario/core/history.py": "70f03b84bd4eaa98712332b97ee492180d91f1663825e8f967cfbb7a9cfce781",
      "scenario/blender/history.py": "3c9e76a4509b88eb3eccb26f3bb6323c759724b62c5b92f0b0f27f5f665a1b6b",
      "scenario/blender/operators.py": "c702667513650b9008e96e1d6f26addd3923a9a29fa19b929251a079bf7214f0",
      "scenario/blender/panels.py": "c198d9e91d272024b696ce0f783f555133bc2b84843e133b510d54b786c16a16",
      "scenario/mcp/tools_scenario.py": "23be0918a72222c90fe91e6878d267f2f782f8d2a40a4db93006d2332c8627fb",
      "scenario/blender/runtime.py": "0b4dc983c64332991b4e46214ef56e275aaa12c673bb1362827e8a1a76d4163e",
      "scenario/blender/model_jobs.py": "93758190ff21f930cea9f664dbdcd5942459058ac0df7e9914dcf991daf8bfae",
      "tests/unit/test_history.py": "47084c58bb62aa7cfd4d31c163b635ce8f4f65313bd10d1b93679c0773612174",
      "tests/blender/test_sdk_history.py": "bee03fca7c05032859098a769a554c3b9b7dc8ad9b4244a22c12ec7d3390ba0c",
      "tests/blender/test_mcp_contracts.py": "4ff84c26aaa5bdb76ef7b91f274163c400dc5db43224a6bfeeee6de7ee36a12b",
      "docs/images/history-saved-job-row.png": "b45ad654d74b7ef9177da0495ded6b30e501b8b35108bcfe76cfec4e0e603e31",
      "docs/images/history-saved-job-recovery.png": "bde44b263afa662e742bb9d1b12427b68d66e999a79239fd7fd822034b9c7537"
    }
  }
}
---

# Scoped saved jobs in cloud history

Evidence for [the canonical guide](../../UI_STYLE.md).
