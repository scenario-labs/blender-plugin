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
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed panels.draw_shared_status and draw_active_job: shared rows map saved states to words, use the reading's status word only in the remote state, draw UILayout.progress with the snapped, floored percentage only when percent is known, and with online access off add the SHARED_OFFLINE_TEXT line for remote, cancel_requested and succeeded rows whether or not a reading exists; otherwise a stale reading adds Status is not updating. A measured fraction below 0.01 floors to a 0% bar. SCENARIO_PT_jobs and SCENARIO_PT_generations split rows with JobRecord.is_terminal. ModelJobs.poll sets the display status through _display_status: a SUCCEEDED record whose results ModelJobs downloads (downloads_results, decided from the saved intent: a workflow, or a model operation whose target is not the Blockout text model) gets the non-terminal awaiting-download, so it stays a Jobs row with its finished on Scenario word and offline Download paused line and Generations does not draw it before its results are saved. A SUCCEEDED prompt, translate or Blockout record keeps the terminal succeeded, so Generations lists it and Jobs never draws it or an offline line; it can reach draw_shared_status only through a Jobs row, so the succeeded offline line is drawn only for a downloading job. Prototype rows keep their previous text. Studio Jobs reuses SCENARIO_PT_jobs.draw. Installed tests check the label, bar arguments, offline lines with and without a reading, a real job drained to succeeded with online access off and drawn through the real SCENARIO_PT_jobs.draw_header and draw and SCENARIO_PT_generations.draw with its real draw_result (1 Job, the finished on Scenario label and the Download paused line, no bar, not listed in Generations), finished Prompt Spark, Translate and Blockout jobs inspected through the Inspect saved jobs operator with online access off and drawn through the same panels (Jobs header, No job running, no Jobs box, listed in Generations, no SHARED_OFFLINE_TEXT line), that SHARED_OFFLINE_TEXT names exactly ModelJobs.NEEDS_SCENARIO, the stale line, the canceling label with a rebound reading, that drawing performs no store reads, ensure calls or meta writes, and pump redraw counts including an online access change. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "683cbe1ba4486ce2e59cc203bbac153d9ea6c31e3f0bc7710cf01bb028019d54",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "3cca6011fa4ce6a1ea72922da75ff8846ae0c6ec0155b00143a6e3c724b8c02d",
      "scenario/blender/model_jobs.py": "ff575c16838b19ef950d8825dc80d8d42c1b81f89a3763f5c50245da091fa33a",
      "scenario/core/jobs/records.py": "afe8476e1232d525de1039a43bc68e8c28c1680fee8fadcacde12285e4c67125",
      "tests/blender/helpers.py": "fdecbd78905c23b88f8400a111f4a8f732fa0b1c8d4825456ad03d73b0137858",
      "tests/blender/test_prompt_tools.py": "3337cbe8e763b7436c69394e3de5b056dd2f02156acc5da3de8307267c275dde",
      "tests/blender/test_blockout_jobs.py": "6151fbd3136147da03d6221962fb8492dd67f60fa2f0748687a44b1367e575b4"
    }
  }
}
---

# Jobs status words and progress bar

Evidence for [the canonical document](../../UI_STYLE.md).
