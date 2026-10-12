---
{
  "type": "Evidence",
  "id": "docs-ui-style.saved-job-action-descriptors",
  "title": "Saved-job controls from shared descriptors",
  "description": "UI rule that saved-job controls come from one descriptor list.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "saved-job-action-descriptors",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that the sidebar Jobs and Generations panels and the Studio Jobs and Results pages draw saved-job controls only through job_recovery.draw_controls, which draws saved_job_actions descriptors; offered actions are drawn enabled and unoffered actions are absent; each operator keeps any confirmation or destination dialog of its own; a shared view without a saved revision draws nothing. Installed Blender 5.1.2 tests on macOS arm64 cover identical view objects across sidebar and Studio pages and ordered descriptor drawing. The rule is policy for later surfaces; no compact composer strip, desktop interaction or screenshot is claimed. Re-checked on main after #370: panels.py and studio.py drift adds the derived history row kind and the Film review page and leaves saved-job drawing on draw_controls; a freshly inspected saved remote job draws no Cancel generation until a refresh confirms an inference job, consistent with hiding an action that is not offered. test_result_actions now runs in the PR baseline. Scoped 2026-10-11 check of the native first-frame control, not a full re-review: saved_job_actions no longer has MCP_ONLY and describes use_first_frame as one scenario.use_saved_first_frame control per asset ID that ModelJobs projects in first_frame_assets, numbered over every saved asset, with no operator icon like the other controls; job_recovery registers that operator; the unit vocabulary, MCP purpose parity and installed registered-property tests include it. Other descriptors, their order and the read-only drawing are unchanged. The claims above still hold; the review date and base revision are unchanged. Re-checked 2026-10-11 after scenario.use_saved_first_frame began discarding its approval when a confirmation is refused: job_recovery.result_actions, draw_action, draw_controls and the operator's registration are unchanged, so the claims above still hold. Re-checked 2026-10-12 after restacking on #377 e8e19109, now on main 4ca693cb, for the sources this change edits: saved_job_actions and job_recovery are byte-identical to the pre-restack head, and test_result_actions still checks use_first_frame against the registered operators and expects no Cancel generation on the saved remote job, as the #370 note above describes. The review date and base revision are unchanged. On 2026-10-12, rechecked against the sources of the saved package import branch after it was rebuilt on main: import_model descriptors are one control per importable unit that ModelJobs projects into view.meta, labelled by format and primary or alternate and numbered by saved-asset index; the unit and installed descriptor tests were updated and the saved-package-import topic reviews that change. Saved-job drawing still goes only through draw_controls. Other claims and the review date are unchanged. On 2026-10-12, rechecked against the sources of the saved splat import branch after it was rebuilt on main, fingerprints were refreshed because saved splat import added splat import labels, session import notice status rows and the splat review options; descriptor ownership, dispatch and read-only drawing claims are unchanged, and the review date is unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason through the shared _refusal wording. This topic's statements were rechecked against that change and are unchanged; only the fingerprints of the sources that change touched were refreshed, other drift is left as it was, and the review date is unchanged.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "scenario/blender/job_recovery.py": "b6e28f0b4c8b1ff282ffc5e2d1a574bde07867a7e94176e667b05ad5232a342e",
      "scenario/blender/panels.py": "c47a4301db4e2383c240dc2bde3dc86fd1d7a910a43c2da4a02dad235e0539b3",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "tests/blender/test_result_actions.py": "db78c091c4cbf3f70e2a3efd216340f816c2219740b9f7186b31bbdd8f3cfe8b",
      "tests/blender/test_runtime_jobs.py": "9cbc0a763541264ae1c3f291a7754c09755066f60dc11f03206ba1fe8f398cf3",
      "tests/blender/test_studio_view.py": "d65762fbbcf6ce9dd63356097697c30b9b22a8fb07bec0866c3ae64e79ad8c7c",
      "tests/blender/run_all.py": "5fa3f8c12ade901f48a21021eba62e61cb80f8e2edac569f67c4f1c54960f195"
    }
  }
}
---

# Saved-job controls from shared descriptors

Evidence for [the canonical document](../../UI_STYLE.md).
