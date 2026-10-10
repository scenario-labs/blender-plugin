---
{
  "type": "Evidence",
  "id": "docs-mcp.workflow-step-decision-tools",
  "title": "Local MCP workflow step review and decision tools",
  "description": "workflow_job_steps reads waiting steps again and decide_workflow_step sends one reviewed decision through ModelJobs.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "workflow-step-decision-tools",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Workflow step decisions section, the workflow and recovery paragraphs, the mapping row and the regenerated tool table against workflow_job_steps, decide_workflow_step, the recover_local_job workflow cancel explanation, the run_workflow, recover_local_job and job_status descriptions, the server instructions, ModelJobs.read_steps, decide, decision_outcome, control and status, and runtime.read_workflow_steps and decide_workflow_step. The hosted tool reference at mcp.scenario.com/docs/tools was read on 2026-10-10: it lists workflow_approve and workflow_reject for human-approval nodes and no selection tool; its parameters were not compared. The API reference page for user approval was read for the ForEach rejection wording. Installed tests on the packaged ZIP with synthetic SDK responses cover a read that keeps an automatically polled job polled and awaits a refresh already in flight, a restarted job that stays paused until a decision, applied, refused (409) and uncertain (503 and timeout) outcomes with one request each, not_sent for a job finished meanwhile, ordered picks, reject persisting canceled, invalid picks, blocked, stale and offline decisions refused before any request, finished and unknown jobs, the workflow cancel explanation with no request, native and MCP decisions seen by each other, a context change after sending, and the tool count; unit tests check the description and schema contracts and the generated table. Tool descriptions and server instructions guide a connected agent; the server cannot verify that a person approved a decision. A live agent client was not exercised. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Re-reviewed on 2026-10-10 after the workflow cancel explanation was limited to a running (remote) workflow job: a prepared, unsent workflow job gets the ordinary refusal and keeps cancel_prepared_job, as an installed test checks with no request, and the recover_local_job description and this document say a running workflow job; the not_sent note now says no decision was sent. Re-reviewed on 2026-10-10 for the native review dialog: the workflow paragraph now says that the dialog in Jobs and Studio sends decisions through the same entry as decide_workflow_step (workflow_steps.send calls runtime.decide_workflow_step), and no longer lists native decision controls as incomplete; the MCP tools are unchanged. Re-reviewed on 2026-10-10 after the review dialog's decision cells became an even split and its minimum width 540; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10 for review asset previews: the MCP tools are unchanged and return no preview or URL; ModelJobs gained review_assets, workflow_nodes preview_assets and workflow_steps the native preview drawing and load operator only; only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 for step links: the workflow_job_steps description and the Workflow step decisions section now list links_complete and the unverified blocked value, disclose the one definition read (SDK workflows.retrieve) the first time a step is seen waiting, and ask the agent to say so before an approval with incomplete links. A unit test checks those phrases in workflow_job_steps and job_status; an installed test reads an unverified live-shaped selection through workflow_job_steps with its blocked_reason and refuses select through decide_workflow_step before any request.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "scenario/mcp/protocol.py": "ee30be5866bbee06918c1145e7e770e90275a4c059c5610d83e6c768a719df7a",
      "scenario/blender/model_jobs.py": "a495102b2780ac37e4260493cea3cfbd8bd0c7130fde4954ae301e511ab701e0",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/blender/workflow_steps.py": "e48ff16971de14b0d350a304a7475af19bf428df642dd199cd72181a2042222c",
      "scenario/core/jobs/workflow_nodes.py": "ed3b7769ac9ad2195bc5a32febf00b1abbd5df027d059a3e9c45918aa0f6ec7a",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/blender/test_workflow_steps.py": "77cdf3ee05fc38f0a99de909b751a50bb6188af72938a339efa0b9bf27baf189",
      "tests/blender/test_mcp_contracts.py": "798a26d219686855675dae4e93c8dd1b127643b2f1824329c898e6f0d2dfb4dc",
      "tests/unit/test_mcp_descriptions.py": "f851bceaa0be3ab114afa3d89023f11cefe5962af7870c53c93d403a1ed2936a",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e"
    }
  }
}
---

# Local MCP workflow step review and decision tools

Evidence for [the canonical document](../../MCP.md).
