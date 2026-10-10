---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.saved-media-playback",
  "title": "Runtime map entry for saved media playback",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Result previews row: the saved media controller draws envelopes for Waveform and opens lane-made private copies for Play and Play in Blender. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Image decoding, still and clip display, MCP parity and live thumbnails remain open.",
    "sources": {
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "tests/blender/test_result_media.py": "07c7686367b0fd38838a82ceafcafb2bd549063335aba11720420985feb1da9a"
    }
  }
}
---

# Runtime map entry for saved media playback

Evidence for [the canonical guide](../../architecture/runtime.md).
