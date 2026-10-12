---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.compact-job-strip",
  "title": "Compact composer job strip status",
  "description": "Adoption status of the compact composer's current-job surface.",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "compact-job-strip",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "c0ca235acec1b47ca39668942e5a659169b8057d",
    "limits": "Reviewed that the compact composer now draws the current shared job's status, progress and at most one explicit action plus Inspect, dispatched through the existing operators, and that dialogs opened from the composer have headless coverage only. Automatic result previews, Unicode/IME, DPI and desktop acceptance remain as the rows state. Installed native tests (tests/blender/test_composer_jobs.py) ran on the packaged ZIP on Blender 5.1.2 macOS arm64 only, over jobs submitted through the synthetic SDK transport of test_model_generation: the real draw handler with recording primitives, the real modal handler with synthetic events, and the real recover_job operator for Resume download. Dialogs and the job card popup opened from inside the composer modal were recorded, not shown; no desktop interaction, screenshot, alternate UI scale, Blender 5.0/5.2 run, other operating system or live provider job is claimed, and that acceptance stays under #66 and #68. Rechecked on 2026-10-12 after rebasing onto main's double-click pairing, kept-in-view card, input-method text field, session lifetime, inference-only cancellation and remote progress changes. The modal pairs double-click presses on the same geometry it dispatches on (_completes_double_click), so a double-click on the tray's background resets the placement and one on a chip dispatches it once; with main's card-only pairing, both new installed tests fail. A card dragged under the headers now stays whole in the viewport, so its tray moves below it, and hides only when the asset shelf also reaches the card. Cancel generation appears only when ModelJobs.actions offers cancel after a poll confirmed an inference job, so a custom job's tray offers Inspect alone. Registration adds the job card after the text field, and the persistent _load_pre still re-initializes the state and its strip caches. The packaged ZIP passes 1,579 installed tests on macOS arm64 Blender 5.1.2, 26 of them in tests/blender/test_composer_jobs.py. Rechecked again after rebasing onto main's Use as video first frame, asset organization and Library changes: the new use_first_frame descriptor joins a saved image's apply group, so an applied Image job's tray reads Reuse... (3) and its job card lists the handoff; the strip and card add no first-frame logic of their own, and RuntimeState.retire_jobs still drops ModelJobs. Rechecked on 2026-10-12 after rebasing onto main's saved mesh package import and saved splat import, and after two review fixes. import_model descriptors are now one per importable unit, labelled by format and primary or alternate (splat units read Import splats), and the view may add status rows for the last import's notices; the strip still dispatches only the descriptors' operators, a single result action as its own chip without its number and several through the job card, and adds no import logic of its own. ModelJobs gains import-unit projection, import notices and a prepare_model command, which busy counts like any other; busy, imports_automatically, bound_views and the rule that a busy job offers nothing but a prepared job's local cancellation are unchanged, and runtime.py only forwards the splat review options. Review fixes: the poll that starts a refresh, download or import lists the job's actions before starting it, so until the next poll the view still lists them while the job is busy, and the strip offered them as live chips. strip_job now passes busy only for a job that is not prepared, and shown_actions holds and remembers whatever such a job's view lists, so a click on one answers that the job is updating. dismiss now keeps only the 64 newest scene forms, as drawn_strips and offered keep 32 regions and 64 jobs. The new strip and dismissal tests and the revised shown_actions test failed on the previous code. The packaged ZIP passes 1,630 installed tests (3 Windows-only skips) on macOS arm64 Blender 5.1.2 only, 28 of them in tests/blender/test_composer_jobs.py.",
    "sources": {
      "scenario/blender/composer/draw.py": "0dde8154cc1d9cd8de04b5456bcdbc5550ad72625ea71f06d0870753f6e2de65",
      "scenario/blender/composer/modal.py": "f6f0ad1b73e6baf2d682b1cf86c604727d635d7e98cded5f885223626a0944e9",
      "scenario/blender/composer/state.py": "22d2ba2af3d28915276b2e94897b97175bbe8445ae3fcc7d89422d39eff965ad",
      "scenario/blender/composer/job_card.py": "cf7f0c9deec08067b0368da1e425932bb03b766ee5f0080721f2b56328747809",
      "scenario/blender/composer/__init__.py": "561f7a9803b1f754202343e3c79cfb67b5851135a421042e34b57a9b3b54839e",
      "scenario/core/ui/job_strip.py": "5c5c08c72a9842192b89bb9006158ac6f7b0234c3ca92bc4af33ffc2c51380bc",
      "scenario/core/ui/composer_layout.py": "69781a9e870670fbc95cf16b82f8337be24a1f3eeadf60dd1f4a654227124a1a",
      "tests/blender/test_composer_jobs.py": "14f0786bfcd19ad7cc77b8257782b569f0c4694467fc3e610e04395d125524e8",
      "tests/unit/test_job_strip.py": "5905c19490b476625d6da98867dc1cccb07b1ed932bed5dfa587df491baa305d",
      "scenario/blender/model_jobs.py": "2f1d9b1f4dfd70898c47590a8b55c76af8f60e2377692e36c85138a4a3187377",
      "scenario/blender/job_recovery.py": "b6e28f0b4c8b1ff282ffc5e2d1a574bde07867a7e94176e667b05ad5232a342e",
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086"
    }
  }
}
---

# Compact composer job strip status

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
