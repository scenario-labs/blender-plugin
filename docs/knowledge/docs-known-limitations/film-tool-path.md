---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-tool-path",
  "title": "Film media tools found only on the inherited PATH",
  "description": "Film finds ffprobe and ffmpeg only on Blender's process PATH, which a Finder or Dock launch on macOS does not extend.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-tool-path",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "3720c9e36eb8ec73382f7158bf4c69c67322eda9",
    "limits": "Reviewed that media_probe.probe_tool resolves ffprobe with shutil.which and otherwise raises 'Install ffprobe on PATH before inspecting Film media', that local_render.media_tools requires both ffmpeg and ffprobe from shutil.which for MP4 capture, and that local_export._verify and film_export.verifier fall back to the Blender decode check without ffprobe; none fetches a binary or changes PATH. A private physical desktop pass on macOS 27.0.1 arm64 Blender 5.1.2, launched with a reduced PATH like a Finder launch, showed the probe error during review preparation; adding the tools to that PATH resolved it. That macOS gives Finder and Dock launches a default PATH without a terminal's additions is platform behavior, not tested here beyond that reduced-PATH session. Windows and Linux launch environments were not examined. Re-checked on 2026-10-12 after the rebase onto main at 2e89cae8 (#408's portable case-study bundle changed local_export and film_export), not a full re-review: every executable lookup in scenario/ is still shutil.which for ffprobe or ffmpeg in media_probe, local_render, local_export._verify and film_export.verifier, the case-study bundle adds none, and the Film PATH bullet is unchanged. Re-checked on 2026-10-12 after the rebase onto main at 3720c9e3: #423 changed only the automatic preview bullet, so the Film PATH bullet and its sources are unchanged.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "743f3b4e39999804dc967f6f108fdfa2008cb8905eed67d58f8c8191809dbb69",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/local_render.py": "fadde8df7fa89d69735f33c2d78682dafc9566c0ef401ab8b2deb6f08a1b912e",
      "scenario/core/jobs/local_export.py": "0fee7cbb34df88e9c70d00cd0574f9e0c347e7d7e53df53a12c33f847b784923",
      "scenario/blender/film_export.py": "042eea294b5ca25eeedfebb225b951be164532cd5dbfd27283733e163f5b4572"
    }
  }
}
---

# Film media tools found only on the inherited PATH

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#interface-and-capture).
