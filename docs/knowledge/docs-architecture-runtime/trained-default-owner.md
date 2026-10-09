---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.trained-default-owner",
  "title": "Trained-model lane defaults follow the credential and project selection",
  "description": "ensure_model_defaults and its retirement on credential, project and reset changes.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "trained-default-owner",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed runtime.ensure_model_defaults, save_model_default, clear_model_default and RuntimeState.retire_model_defaults, called from the credential/project retirement branch of sync_catalog_context and from reset; preference update callbacks in prefs.py drive that branch. Installed-ZIP tests show the owner opens without a job session, manager, connection check or catalog load with online access off; a project or credential change retires it and isolates defaults; returning to a selection reopens its saved defaults; a whitespace-only project edit keeps the owner; a stale context token is refused; reset retires and reopens; missing credentials create no files. Installed-ZIP suite on Blender 5.1.2, Python 3.13.9, macOS 27.0.1 arm64: 1213 tests OK (2 Windows-only skips), including the seven ModelDefaultsRuntimeTests; ZIP sha256 0d675ed1734d9080f7845e678df1c741b2151e3ffc0be36efc59d6258f9db6a1, whose scenario sources match git archive of the reviewed head. MCP tools and native controls do not call it yet; physical UI and MCP threading were not exercised.",
    "sources": {
      "scenario/blender/runtime.py": "4389630c31be63af3ca76f146712d3d4ca197550ae04899bd1e80c394bde637a",
      "scenario/prefs.py": "569ef8524cb0ba9e7d8f5b46582d4903b05d96a7cbc6cf1f2b3216be23c4ba96",
      "scenario/core/jobs/model_defaults.py": "1e4fbf2f0cfb8de6cefd1a45ea82bbb0ecad9a1dd179f3a98b71519ca61dd93d",
      "tests/blender/test_model_defaults.py": "d9ee6a5c75418fe71f27c37c894967f3a0fc6d294debdfbf330bb0ccaa8029aa"
    }
  }
}
---

# Trained-model lane defaults follow the credential and project selection

Evidence for [the canonical document](../../architecture/runtime.md).
