---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Limitation wording reviewed against the export primitive: session commands exist without native/MCP controls, verification strength depends on ffprobe and Blender builds without H.264/AAC cannot export. The case-study bundle is absent.",
    "sources": {
      "scenario/blender/film_export_worker.py": "3078e5770af2245c84690a2dff7509aa235ed053052da04e64cd2ef4426ad04f",
      "scenario/blender/job_session.py": "96ed0e4825912df5de7dd939c8e963f7846e268326e256441e6c2e618801c55c",
      "scenario/blender/local_capture.py": "79391e7f3eb1f59c07bc948ec267841ce4ef682159437aae64b9b03b21fc6dd7",
      "scenario/core/jobs/local_export.py": "ca449fe8eb3969af94534488bfadd3789c98985205dc421225431398c4a81164",
      "scenario/core/jobs/local_render.py": "3d6172f16877deb9397bd4057c934af05acac3e762e3e9d94eb7ac495561da6c",
      "scenario/core/jobs/mp4_inspection.py": "daaf36bdc305f1735f1fea471c621537298fbffc4963657209489a89505ce041",
      "tests/unit/test_local_export.py": "e941073573fed89af84a19ff91a15d890a7af36b93896fe0e4a03c696fe325af"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
