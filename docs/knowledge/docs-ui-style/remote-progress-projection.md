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
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed panels.draw_shared_status and draw_active_job: shared rows map saved states to words, use the reading's status word only in the remote state, draw UILayout.progress with the snapped, floored percentage only when percent is known, and with online access off add the SHARED_OFFLINE_TEXT line for remote, cancel_requested and succeeded rows whether or not a reading exists; otherwise a stale reading adds Status is not updating. A measured fraction below 0.01 floors to a 0% bar. SCENARIO_PT_jobs and SCENARIO_PT_generations split rows with JobRecord.is_terminal. ModelJobs.poll sets the display status through _display_status: a SUCCEEDED record whose results ModelJobs downloads (downloads_results, decided from the saved intent: a workflow, or a model operation whose target is not the Blockout text model) gets the non-terminal awaiting-download, so it stays a Jobs row with its finished on Scenario word and offline Download paused line and Generations does not draw it before its results are saved. A SUCCEEDED prompt, translate or Blockout record keeps the terminal succeeded, so Generations lists it and Jobs never draws it or an offline line; it can reach draw_shared_status only through a Jobs row, so the succeeded offline line is drawn only for a downloading job. Prototype rows keep their previous text. Studio Jobs reuses SCENARIO_PT_jobs.draw. Installed tests check the label, bar arguments, offline lines with and without a reading, a real job drained to succeeded with online access off and drawn through the real SCENARIO_PT_jobs.draw_header and draw and SCENARIO_PT_generations.draw with its real draw_result (1 Job, the finished on Scenario label and the Download paused line, no bar, not listed in Generations), finished Prompt Spark, Translate and Blockout jobs inspected through the Inspect saved jobs operator with online access off and drawn through the same panels (Jobs header, No job running, no Jobs box, listed in Generations, no SHARED_OFFLINE_TEXT line), that SHARED_OFFLINE_TEXT names exactly ModelJobs.NEEDS_SCENARIO, the stale line, the canceling label with a rebound reading, that drawing performs no store reads, ensure calls or meta writes, and pump redraw counts including an online access change. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "8c9ed56c0d83b4c0cfd4578e7158c05f1df895f7c2765319c0894c1ca0491e83",
      "scenario/blender/pump.py": "d146e694610b8ec4ca23b4577da1d792d4ae2c0dbc8d7a8a88d690571a330acd",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "e3a6885f17b3e800ebf6e1d43c0328e2fc87f1eb3a7a903325b0f75aa4f701c4",
      "scenario/blender/model_jobs.py": "5a378d786f8c775bf097673c9962f449a868506e234ed9e829f0d221ad059d4f",
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
