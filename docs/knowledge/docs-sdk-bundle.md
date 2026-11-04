---
{
  "type": "Evidence",
  "id": "docs-sdk-bundle",
  "title": "docs/SDK_BUNDLE.md evidence",
  "evidence": {
    "path": "docs/SDK_BUNDLE.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-11-04",
    "reviewed_revision": "a316f6a00c2c126d63e349f492fd9340d7ca7e3b",
    "limits": "Source-reviewed against the wheel lock, manifest, uv.lock, bundle tools and installed-runtime tests. No native Blender run, live Scenario call or macOS execution; CI matrix results must be inspected per run.",
    "sources": [
      ".github/workflows/blender-baseline.yml",
      "pyproject.toml",
      "scenario/blender_manifest.toml",
      "scenario/core/api/sdk_adapter.py",
      "scenario/sdk-wheel-lock.json",
      "tests/blender/test_sdk_bundle.py",
      "tests/unit/test_scenario_sdk_contract.py",
      "tests/unit/test_wheel_bundle.py",
      "tools/build.py",
      "tools/test_blender.py",
      "tools/wheel_bundle.py",
      "tools/zip_limits.py",
      "uv.lock"
    ]
  }
}
---

Evidence for [the canonical document](../SDK_BUNDLE.md).
