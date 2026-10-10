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
    "limits": "Reviewed the Workflow step decisions section, the workflow and recovery paragraphs, the mapping row and the regenerated tool table against workflow_job_steps, decide_workflow_step, the recover_local_job workflow cancel explanation, the run_workflow, recover_local_job and job_status descriptions, the server instructions, ModelJobs.read_steps, decide, decision_outcome, control and status, and runtime.read_workflow_steps and decide_workflow_step. The hosted tool reference at mcp.scenario.com/docs/tools was read on 2026-10-10: it lists workflow_approve and workflow_reject for human-approval nodes and no selection tool; its parameters were not compared. The API reference page for user approval was read for the ForEach rejection wording. Installed tests on the packaged ZIP with synthetic SDK responses cover a read that keeps an automatically polled job polled and awaits a refresh already in flight, a restarted job that stays paused until a decision, applied, refused (409) and uncertain (503 and timeout) outcomes with one request each, not_sent for a job finished meanwhile, ordered picks, reject persisting canceled, invalid picks, blocked, stale and offline decisions refused before any request, finished and unknown jobs, the workflow cancel explanation with no request, native and MCP decisions seen by each other, a context change after sending, and the tool count; unit tests check the description and schema contracts and the generated table. Tool descriptions and server instructions guide a connected agent; the server cannot verify that a person approved a decision. A live agent client was not exercised. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Re-reviewed on 2026-10-10 after the workflow cancel explanation was limited to a running (remote) workflow job: a prepared, unsent workflow job gets the ordinary refusal and keeps cancel_prepared_job, as an installed test checks with no request, and the recover_local_job description and this document say a running workflow job; the not_sent note now says no decision was sent.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "015351c9b65663f5209ebf2c29996a3da4e8f6c6595822462aa573cec64c3838",
      "scenario/mcp/protocol.py": "ee30be5866bbee06918c1145e7e770e90275a4c059c5610d83e6c768a719df7a",
      "scenario/blender/model_jobs.py": "69e1baa892ea691fccec82b28cc294bbfeb0672053d629ebca839ff3d8364022",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/core/jobs/workflow_nodes.py": "24a72b8fdeffe9ff9540d5fd57fff10ece53559bbc5ab571880c00298f537a51",
      "tests/blender/test_workflow_commands.py": "928f4e45ae6c7d3e44e87dda2c7914f6f6ff3a26a85ab707e7ee3d91c68e898e",
      "tests/blender/test_mcp_contracts.py": "798a26d219686855675dae4e93c8dd1b127643b2f1824329c898e6f0d2dfb4dc",
      "tests/unit/test_mcp_descriptions.py": "6608299daa0eb4928d2884166e76a958ff4b21bc195d3b8634a1ff3747e1e381",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e"
    }
  }
}
---

# Local MCP workflow step review and decision tools

Evidence for [the canonical document](../../MCP.md).
