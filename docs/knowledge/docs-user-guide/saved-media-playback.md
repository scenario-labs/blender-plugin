---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-media-playback",
  "title": "Play and waveform controls for saved video and audio",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Video, Audio, panel summary and Files and folders claims about saved-result Play, Play in Blender and Waveform: their place in Jobs and Generations, private read-only copies named by the saved type, the credential-free animation player and its two-player limit, offline operation, Cancel, Retry and close, receipt-keyed envelope reuse, retirement on a connection change or file load, and the format and size limits. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Soundtrack playback in Blender's animation player is stated as unverified. The retained prototype controls' wording and the older panel screenshots were not re-reviewed.",
    "sources": {
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/ui/saved_job_actions.py": "075c3dbe813629c45bbb28c6c3a79a43d4f282454a68ee2e9e3fef8f62fbe2d6",
      "scenario/blender/job_recovery.py": "4b237b2c40e440f138a2fe5d21c6a6398221074c47edf88b9f7cd1389ba1b267",
      "scenario/blender/panels.py": "3fbc87ec9c92f91e619527b99f166303ee3a7628c056bba6b804325a16cff3c6",
      "tests/blender/test_result_media.py": "9d0b4a6075dbcbef4e402606fe63d1f3d965cc869ba377a812b7758a5af98b89",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Play and waveform controls for saved video and audio

Evidence for [the canonical document](../../USER_GUIDE.md).
