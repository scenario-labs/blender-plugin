---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-media-playback",
  "title": "Playback descriptors and player copy ownership",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the playback descriptors' saved-state and media-type conditions, their operators' context, revision and receipt checks, JobSession.prepare_playback and cancel_playback on the preview lane, and the controller's ownership: latest-request opening, reuse, the copy and player budgets, envelope-only waveform requests, scheduler cancellation, late-result rejection and cleanup on retirement, file load and unregister, including a persistent update timer that survives a file load and a retirement that first reaps exited animation players. The animation player environment omits SCENARIO_, PYTHON and proxy variables. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed job_session.py (Film export, Film review commands, upload restart, an undo step for saved model imports, first-frame verification and asset organization review entry points), saved_job_actions.py (native first-frame descriptors replacing the MCP-only handoff, and World candidate numbering), job_recovery.py (the native Use as video first frame review operator) and runtime.py (explicit lane model defaults, the first-frame application, the Film review poll, an older-history error reset, the asset organization pump and the Library poll after it); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/job_session.py": "32cb7d9b8a929038b37bcf0979625076f1d9d1bf699f25cf3cd65439cc13e567",
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/core/ui/saved_job_actions.py": "7648560ca76f49835e680fdad677dae5537db9c5de5c5393874c25b81a9916eb",
      "scenario/blender/job_recovery.py": "2480e375c1a9c16a3bd84bd2975ad6276084d659d1bfaa82cca36367fe1b57af",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/blender/runtime.py": "184975579304728ea00b3d84bc7d4bee5b308380bfa923a97aeb2f8cdc23d518",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c"
    }
  }
}
---

# Playback descriptors and player copy ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
