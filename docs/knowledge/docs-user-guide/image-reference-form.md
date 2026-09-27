---
{
  "type": "Evidence",
  "id": "docs-user-guide.image-reference-form",
  "title": "Guarded Image reference upload controls",
  "description": "Explicit reference upload, original-slot attachment and subsequent exact quoting.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "image-reference-form",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected explicit Image upload admission, saved duplicate-admission markers, credential-scope binding, main-thread scene/model/slot guards, read-only drawing and inspection, and quote invalidation. Native synthetic tests cover changed/deleted slots, stale scenes, duplicate clicks, scope changes, pending Render Result request construction, and an upload-to-exact-quote-to-single-submission journey. The exact candidate passed 483 native tests each on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS ARM64. Isolated offline before/after captures of the final candidate on Blender 5.2.1 were visually inspected and showed one programmatic upload attached; the normal profile remained unchanged. Physical input/focus/viewport interaction remains unverified because the computer-control tool could not bind the disposable window. No live Scenario/S3 requests, native upload recovery/reattachment or complete #65/#37 acceptance is claimed. Parent upload/recovery and other generation lanes remain separate evidence.",
    "sources": {
      "scenario/blender/reference_form.py": "552ab8f44f0d9e3c8335cca7ff5800f9884825fbe3a1b386643bb3524b0ff82f",
      "scenario/blender/reference_uploads.py": "33ec70011cff2a4745a2a41528d3b32ae8174e23c9743b2369e22ce39c91c4aa",
      "scenario/blender/generation.py": "add487ba125ff012dcd0f73acaa1640d91f1a8be4eda71008c7c9c36e3972832",
      "scenario/blender/panels.py": "e6d111cfe95e3994869c13b672a4e5b8bd966c86e4b0d71a47d788a0638bc214",
      "scenario/blender/registry.py": "8aa426a4509bda15fb0b7d4caece1e5e4a21847cedf62440a6e1072e1dc8fe88",
      "scenario/blender/job_session.py": "6df07b116f3eea2efb46a6cfe2f60025ec3a0ba821119c181378f14e26dd7ab8",
      "tests/blender/test_reference_form.py": "5d1ed81a1f45dcb8dfcfbe0cec3a337d7038a2448cca5b570ebf9f99786e1b73",
      "tests/blender/test_reference_uploads.py": "b81d4de08acd24f24176709276674c7d7035a5acd04cfa720e2e721dfda9140e",
      "tests/blender/run_all.py": "e54a562f8d8953642ed8f8e0090926a30d76567ebb28fa14b8b106de9cddd8c6"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
