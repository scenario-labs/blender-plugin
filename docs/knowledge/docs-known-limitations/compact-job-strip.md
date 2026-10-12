---
{
  "type": "Evidence",
  "id": "docs-known-limitations.compact-job-strip",
  "title": "Compact job strip limits",
  "description": "Known limits of the composer's current-job tray.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "compact-job-strip",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that only ModelJobs.submit records a JobBinding (submit_workflow, submit_film, inspect and cloud recovery create unbound views), that strip_placement hides the tray when neither position fits between the vertical insets, that a held action answers JOB_BUSY without dispatch while ModelJobs.busy, and that the composer modal's dialogs and job card are covered only by recorded calls in background Blender. Installed native tests (tests/blender/test_composer_jobs.py) ran on the packaged ZIP on Blender 5.1.2 macOS arm64 only, over jobs submitted through the synthetic SDK transport of test_model_generation: the real draw handler with recording primitives, the real modal handler with synthetic events, and the real recover_job operator for Resume download. Dialogs and the job card popup opened from inside the composer modal were recorded, not shown; no desktop interaction, screenshot, alternate UI scale, Blender 5.0/5.2 run, other operating system or live provider job is claimed, and that acceptance stays under #66 and #68. Rechecked on 2026-10-12 after rebasing onto main's double-click pairing, kept-in-view card, input-method text field, session lifetime, inference-only cancellation and remote progress changes. The modal pairs double-click presses on the same geometry it dispatches on (_completes_double_click), so a double-click on the tray's background resets the placement and one on a chip dispatches it once; with main's card-only pairing, both new installed tests fail. A card dragged under the headers now stays whole in the viewport, so its tray moves below it, and hides only when the asset shelf also reaches the card. Cancel generation appears only when ModelJobs.actions offers cancel after a poll confirmed an inference job, so a custom job's tray offers Inspect alone. Registration adds the job card after the text field, and the persistent _load_pre still re-initializes the state and its strip caches. Only ModelJobs.submit still records a JobBinding. The packaged ZIP passes 1,579 installed tests on macOS arm64 Blender 5.1.2, 26 of them in tests/blender/test_composer_jobs.py. Rechecked again after rebasing onto main's Use as video first frame, asset organization and Library changes: the new use_first_frame descriptor joins a saved image's apply group, so an applied Image job's tray reads Reuse... (3) and its job card lists the handoff; the strip and card add no first-frame logic of their own, and RuntimeState.retire_jobs still drops ModelJobs.",
    "sources": {
      "scenario/blender/composer/draw.py": "c620b16740877ed1094839e4b9d44961b3cfe8d7730d0ccc87ee6f55f0524132",
      "scenario/blender/composer/modal.py": "f6f0ad1b73e6baf2d682b1cf86c604727d635d7e98cded5f885223626a0944e9",
      "scenario/blender/composer/state.py": "a71bbd1a1497c199a6835387dac27249b339b9a6397b992be56cf3cddaa35b66",
      "scenario/blender/composer/job_card.py": "cf7f0c9deec08067b0368da1e425932bb03b766ee5f0080721f2b56328747809",
      "scenario/blender/composer/__init__.py": "561f7a9803b1f754202343e3c79cfb67b5851135a421042e34b57a9b3b54839e",
      "scenario/core/ui/job_strip.py": "5c5c08c72a9842192b89bb9006158ac6f7b0234c3ca92bc4af33ffc2c51380bc",
      "scenario/core/ui/composer_layout.py": "69781a9e870670fbc95cf16b82f8337be24a1f3eeadf60dd1f4a654227124a1a",
      "tests/blender/test_composer_jobs.py": "b654fb0911433269b8ba6b821c2df39b34be85d8eed0e57fd9434a8cbac5aeaa",
      "tests/unit/test_job_strip.py": "c89a08d5dbb4b52df1fe0b8d811744e85e7070fd32fc644a98d00bc08afebe39",
      "scenario/blender/model_jobs.py": "404a5623352d9a919326d5b36a1b96b5cc130b0a99672702fac4acf16a94f110",
      "scenario/blender/job_recovery.py": "708183b9df9637902b40c3c2cff0c7a6c9e13bb2b8a2ba474ea212d2b34a2a6a",
      "scenario/core/ui/saved_job_actions.py": "8dc3f4dd9b5272b1c1ba15818c36f4e0971afaa5ee5b85e491a17d46185de494"
    }
  }
}
---

# Compact job strip limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
