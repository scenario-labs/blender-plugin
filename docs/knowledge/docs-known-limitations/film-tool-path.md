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
    "base_revision": "ff8d29d879487719fde8fd9b4089438ae0ba2c78",
    "limits": "Reviewed that media_probe.probe_tool resolves ffprobe with shutil.which and otherwise raises 'Install ffprobe on PATH before inspecting Film media', that local_render.media_tools requires both ffmpeg and ffprobe from shutil.which for MP4 capture, and that local_export._verify and film_export.verifier fall back to the Blender decode check without ffprobe; none fetches a binary or changes PATH. A private physical desktop pass on macOS 27.0.1 arm64 Blender 5.1.2, launched with a reduced PATH like a Finder launch, showed the probe error during review preparation; adding the tools to that PATH resolved it. That macOS gives Finder and Dock launches a default PATH without a terminal's additions is platform behavior, not tested here beyond that reduced-PATH session. Windows and Linux launch environments were not examined.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "40654c5a1f5943fe87ce5d90b490b07681a754778e10e94ef6a7514c6ca45b1c",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/local_render.py": "fadde8df7fa89d69735f33c2d78682dafc9566c0ef401ab8b2deb6f08a1b912e",
      "scenario/core/jobs/local_export.py": "781e9c64cc62c8380d480b264eadcf9bcff7e80f2256037d70bea915e6af5bc6",
      "scenario/blender/film_export.py": "b34df0eac54a4ea16947cbaf8a20b952cec6cfff99fc230e899543060210fd8c"
    }
  }
}
---

# Film media tools found only on the inherited PATH

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#interface-and-capture).
