---
{
  "type": "Evidence",
  "id": "docs-known-limitations.waiting-workflow-steps",
  "title": "Waiting workflow step limits",
  "description": "Rejecting a waiting step is the only workflow stop; nested steps, loop-fed selections, previews and live behavior remain limited.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that ModelJobs.control refuses cancel on a running workflow job with WorkflowCancelUnavailable and that rejection through ModelJobs.decide is the only stop; that pending_steps reads top-level flow nodes only; that a selection feeding a ForEach loop, a nested workflow or an unlisted node type is blocked to reject only; that steps carry asset IDs or text and no preview is loaded; and that the native dialog draws at most 12 wrapped lines per text candidate. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session.",
    "sources": {
      "scenario/blender/model_jobs.py": "5588e3c4ad43bdd8eba1239fa5b7134217dd2f68900b4c038e7d6b4766906cc2",
      "scenario/blender/workflow_steps.py": "82c868fd18b362c83c494b72445165f8b1144218c33261ea32d4fe933f397f71",
      "scenario/core/jobs/workflow_nodes.py": "24a72b8fdeffe9ff9540d5fd57fff10ece53559bbc5ab571880c00298f537a51",
      "scenario/mcp/tools_scenario.py": "015351c9b65663f5209ebf2c29996a3da4e8f6c6595822462aa573cec64c3838",
      "tests/unit/test_workflow_nodes.py": "6ce785fc0d27f15b59190a83b4aaa02e0bc3f15fb80ecc82af0ecbb4a794c64e",
      "tests/blender/test_workflow_steps.py": "530ba44c89c0ac09aaa415f6bec0e34ec5b12aba6e61d1525a3000a990fd8e77",
      "tests/blender/test_workflow_commands.py": "928f4e45ae6c7d3e44e87dda2c7914f6f6ff3a26a85ab707e7ee3d91c68e898e"
    }
  }
}
---

# Waiting workflow step limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
