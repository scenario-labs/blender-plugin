---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.temporary-preview-decode",
  "title": "Temporary preview decoding outside the open blend file",
  "description": "Main-thread bounded image decoding inside bpy.data.temp_data() that leaves captured job origins current.",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "temporary-preview-decode",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the helper's temporary-block decode, fit, unpremultiplied linear-to-sRGB encoding of float pixels, 8-bit RGBA PNG output, sanitized errors, path-object checks, reference lifetime including the error traceback's helper-frame locals, and main-thread guard, plus the JobSession dependency handler and origin revisions it must not trigger. Installed native tests cover generated 8-bit PNG, HALF and FLOAT OpenEXR, a semi-transparent HALF OpenEXR decoded to straight display values and through the PNG output, PNG output, limit refusal, unreadable and missing files with and without output, with no block reference in the error context or helper-frame traceback locals, string paths checked as path objects, refusal of a path the check rejects and of a Windows path its UTF-16 encoding cannot represent (a lone surrogate, through the real check on Windows path objects and as a raised UnicodeEncodeError), each with no original error as cause or context, and worker-thread refusal, with open-file images, scenes and dirty flag unchanged, no dependency ID updates, a captured origin still current and preparable, and a main-data load/remove control that invalidates it. Dependency observations and native runs are macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 only; Linux and Windows rely on hosted CI. The helper performs no header, dimension or format check before Blender loads a file; callers own that bound. 16-bit PNG, JPEG and WebP inputs were not exercised; locally, Windows path handling was exercised only through that check on Windows path objects, on Blender 5.1.2. No UI, MCP, preview cache or Scenario operation uses it yet; no human review is implied.",
    "sources": {
      "scenario/blender/preview_decode.py": "e4e201cc9202e4008cfff17f8b5377a62169120359c5517b1907a23fd87d7eef",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "scenario/core/jobs/origins.py": "d1282d67aacdfe2444a776cf1338667bea9ee67392ff3f473db581a0f8059977",
      "scenario/core/jobs/local_render.py": "37c57537f75172892b868c56c9e0bcb641617c271ec1dae5a037e96ecabaeaf8",
      "tests/blender/test_preview_decode.py": "19d43c52f1956a4b01e2c63fa3441baf4797332c28d93feb721885d7620d6a58",
      "tests/blender/helpers.py": "7e11a66ebd38211c2676471d4d1abb40d69bdf27cf5c69316436dc51ec197f7d",
      "tests/blender/run_all.py": "12f31ad1ecdb05cc5821c6468365693098af05bec698971832a86542514c52ad"
    }
  }
}
---

# Temporary preview decoding outside the open blend file

Evidence for [the canonical document](../../architecture/blender.md).
