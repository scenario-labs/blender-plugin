---
{
  "type": "Evidence",
  "id": "docs-ui-style.offline-generation-status",
  "title": "Offline generation status",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "offline-generation-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "252b25a3825a3a0c97a694fe6f7f55fb9c64e459",
    "limits": "Source-reviewed offline display, pending estimate retention and Image ready-handle presentation guards. Submission still validates exact quotes. Native tests use an offline SDK transport; this does not certify live pricing, all keyboard layouts or integrated release acceptance.",
    "sources": {
      "docs/UI_STYLE.md": "0d081869e3efe7c4cba708eedf524e4304c621d2d802658884c6c5e16c22ae24",
      "scenario/blender/panels.py": "6387af1a3be867970291c43a6367b001b4f62765efd5d217d4353d454bafccfe",
      "scenario/blender/pump.py": "9da80b20919f9e9c94d6f584725f82e404e44b2c9c6d3bf6fbd04d1bfe2c5e16",
      "scenario/blender/composer/draw.py": "05d1bdd0ef55ac78775207822ea0696daeb2c3934395b3b20d21dd83bb0b9128",
      "scenario/blender/composer/modal.py": "cfb3f7a59f1c96208a76680921938f1237bbab3b990e9cd59b2c3c2a00aa87a2",
      "tests/blender/test_sdk_estimates.py": "fe5a6223644af8b64531bcb2349f97190fac72a9411e6e91994e11061700c6c0"
    }
  }
}
---

# Offline generation status

Supports the [UI style guide](../../UI_STYLE.md#buttons) for offline composer labels,
disabled Image actions and estimates retained until network access returns.
