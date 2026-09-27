---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.image-reference-form",
  "title": "Guarded Image reference upload controls",
  "description": "Explicit reference upload, session-owned recovery, confirmed saved-image attachment and subsequent exact quoting.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "image-reference-form",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected explicit Image upload admission, typed pre-admission rejection, saved duplicate-admission markers, credential-scope binding, main-thread scene/model/slot guards, read-only drawing, paginated inspection, session-owned recovery and single-use recovered-reference confirmation. Native synthetic tests cover transient timer context, corrected local validation failures, retained asynchronous uncertainty, changed/deleted slots, stale destinations, scope changes, actual blend save/reopen, absent MCP completion callbacks, cleanup failures preserving original files, and upload-to-exact-quote-to-single-submission. The exact candidate passed 494 native tests each on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS ARM64. Isolated offline Blender 5.2.1 captures of the candidate inspector and attachment confirmation were visually inspected; the normal profile remained unchanged. Physical input/focus/viewport interaction remains unverified. No live Scenario/S3 acceptance or complete #65/#37 acceptance is claimed. Other generation lanes remain separate evidence.",
    "sources": {
      "scenario/blender/reference_form.py": "7172f20994659f65951f3bf0e3e09954da370a8de3c8dfdb341cec43c225e096",
      "scenario/blender/reference_uploads.py": "361bc6c94f3b768f9c9c66fc8a02cf07bc363da37b4782484411c2dd9b89aa2f",
      "scenario/blender/generation.py": "add487ba125ff012dcd0f73acaa1640d91f1a8be4eda71008c7c9c36e3972832",
      "scenario/blender/panels.py": "6e30e950823ede61f9f088d6cf290205cb4db50b37929f431d2c20673dd8b065",
      "scenario/blender/registry.py": "8aa426a4509bda15fb0b7d4caece1e5e4a21847cedf62440a6e1072e1dc8fe88",
      "scenario/blender/job_session.py": "6df07b116f3eea2efb46a6cfe2f60025ec3a0ba821119c181378f14e26dd7ab8",
      "tests/blender/test_reference_form.py": "fff5b91e60efa4738d055a99d4f7a0ce9c90fa1a8e56711fad972858db3975b3",
      "tests/blender/test_reference_uploads.py": "261f22f9eb81ef5620e998438601cc57fd70f3dfd4b4cc0a95e8661199cca4bb",
      "tests/blender/run_all.py": "e54a562f8d8953642ed8f8e0090926a30d76567ebb28fa14b8b106de9cddd8c6",
      "scenario/mcp/tools_scenario.py": "527d2ca7b16a25152f19ec113ba2b2761be9e467ce66b1c14256e796a7d465b6"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_UPLOADS.md).
