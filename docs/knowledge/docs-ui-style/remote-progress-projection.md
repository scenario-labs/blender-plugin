---
{
  "type": "Evidence",
  "id": "docs-ui-style.remote-progress-projection",
  "title": "Jobs status words and progress bar",
  "description": "UI rule for shared Jobs rows, the progress bar and stale lines.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed panels.draw_shared_status and draw_active_job: shared rows map saved states to words, use the reading's status word only in the remote state, draw UILayout.progress with the snapped, floored percentage only when percent is known, and with online access off add the SHARED_OFFLINE_TEXT line for remote, cancel_requested and succeeded rows whether or not a reading exists; otherwise a stale reading adds Status is not updating. A measured fraction below 0.01 floors to a 0% bar. SCENARIO_PT_jobs and SCENARIO_PT_generations split rows with JobRecord.is_terminal. ModelJobs.poll sets the display status through _display_status: a SUCCEEDED record whose results ModelJobs downloads (downloads_results, decided from the saved intent: a workflow, or a model operation whose target is not the Blockout text model) gets the non-terminal awaiting-download, so it stays a Jobs row with its finished on Scenario word and offline Download paused line and Generations does not draw it before its results are saved. A SUCCEEDED prompt, translate or Blockout record keeps the terminal succeeded, so Generations lists it and Jobs never draws it or an offline line; it can reach draw_shared_status only through a Jobs row, so the succeeded offline line is drawn only for a downloading job. Prototype rows keep their previous text. Studio Jobs reuses SCENARIO_PT_jobs.draw. Installed tests check the label, bar arguments, offline lines with and without a reading, a real job drained to succeeded with online access off and drawn through the real SCENARIO_PT_jobs.draw_header and draw and SCENARIO_PT_generations.draw with its real draw_result (1 Job, the finished on Scenario label and the Download paused line, no bar, not listed in Generations), finished Prompt Spark, Translate and Blockout jobs inspected through the Inspect saved jobs operator with online access off and drawn through the same panels (Jobs header, No job running, no Jobs box, listed in Generations, no SHARED_OFFLINE_TEXT line), that SHARED_OFFLINE_TEXT names exactly ModelJobs.NEEDS_SCENARIO, the stale line, the canceling label with a rebound reading, that drawing performs no store reads, ensure calls or meta writes, and pump redraw counts including an online access change. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. Scoped 2026-10-12 check of the Render Video first-frame handoff, not a full re-review: ModelJobs adds the use_first_frame action, its single-use approval, the verify_first_frame command and the session-local first_frame status field; polling, delivery predicates, progress projection, bindings and other actions are unchanged. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-11 check of the native first-frame control, not a full re-review: ModelJobs.poll also writes first_frame_assets, the eligible still asset IDs, into each saved view's meta for the native descriptor; status words, progress, delivery, offline lines and redraws are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/panels.py": "6865424bb96bd545a60a72ae5fad6531eccc97016fdd8eac21857d29eecf5415",
      "scenario/blender/pump.py": "d146e694610b8ec4ca23b4577da1d792d4ae2c0dbc8d7a8a88d690571a330acd",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "505d6e569450a339535038db01c26484550a6bfd0bc0c1dffb1d35d207da8df9",
      "scenario/blender/model_jobs.py": "69e3c0a37db957710dcfd534ea0552a79b0a425f84cbf7d859e120ff9598b563",
      "scenario/core/jobs/records.py": "afe8476e1232d525de1039a43bc68e8c28c1680fee8fadcacde12285e4c67125",
      "tests/blender/helpers.py": "de6a4841486130ed22e5a67d006fe859b27d2f0af5246ca4d87b9229d2a298f5",
      "tests/blender/test_prompt_tools.py": "a9c04c117248f0630d8a9f02af2df95357904fae5ae767e260a97d0531d9a10b",
      "tests/blender/test_blockout_jobs.py": "94a8e8157b551e2604229b3d5a57df0e9a74b8572476fbd527a077b4ff8a4069"
    }
  }
}
---

# Jobs status words and progress bar

Evidence for [the canonical document](../../UI_STYLE.md).
