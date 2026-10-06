---
{
  "type": "Evidence",
  "id": "docs-ui-style.cloud-history-recovery",
  "title": "Shared cloud history recovery entry points",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "cloud-history-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "ea77f3a542be698301bd0a414579d4a9e40650bb",
    "limits": "Inspected native/MCP cloud adoption, bounded pending reads, caller-owned completed read delivery, stable shared/prototype row merging, paused saved views and destination approval. The corrected exact package passes 764 installed tests each on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, including delayed delivery after cache eviction/replacement, foreign-owner rejection, 55 retained shared rows with 60 prototype updates and collision precedence. Prior desktop proof and screenshots remain specific to ZIP e572909c23aae8ddd027aa48e489f338eb34dd35b2eacdaf35cbb9a7c57f11ec; fresh input proof for the review fix is pending because computer control cannot locate its running window. No live cloud refresh, provider latency, completed result application, other OS/DPI or integrated release acceptance; no prototype migration.",
    "sources": {
      "scenario/blender/model_jobs.py": "c749cfa4693bb8ccefc10af8543ce1536c8aab35923ca71199fa38b80318eb50",
      "scenario/blender/generation.py": "0d53b27213d1eb0f476bf46e13e96b51afdd85b7ca921462bdf87e3853940b7e",
      "scenario/blender/operators.py": "4de1ebb739f8163d9a2d1cec4052290a7bde372e40972f17517c6cd3029ddab1",
      "scenario/blender/panels.py": "a6d70fce03b372a471bd004542c954d220b01cab5da962cf60e1799c572fc798",
      "scenario/mcp/tools_scenario.py": "1f0cf79f3205c4f6972a87c8704d5f0faecfccb177fbf6edbbdb1c61681dca0d",
      "scenario/blender/job_session.py": "72dbb693cc852bb2e123aad6e2af5b3772449c446456c7eca678245a17188dc9",
      "scenario/core/jobs/coordinator.py": "70788f976e8fe429f594525e09e00f97833b9f09840fd69eb4446fa83e932eb2",
      "tests/blender/test_model_generation.py": "e4c2abe9e294a9fb3c6a6cc81fad7c7069aec00fa7d08560ff8f187546dd63be",
      "tests/blender/test_sdk_history.py": "78584d9ce3217b28f82e1ca9e2cc870b1470a444c7ee98a39cc59b3f2b8369e4",
      "tests/blender/test_mcp_contracts.py": "9917e64d6283f12a070d6c22619bf2628bfb6aeebdd86f87d61f3b6d5a5dda83",
      "tests/unit/test_mcp_descriptions.py": "26de29defdfc81f1766e9308c2c2867fdfaecbd354104856436c07b53b36ba42",
      "docs/images/cloud-history-recovery-controls.png": "70b35ac53d4c848d9ed4ed92dde79ff8c553551bc61d5bf13cb7934d6da934ac",
      "docs/images/cloud-history-recovery-saved.png": "af4f05fa7c5acdd9eda18770b770d7b46c0d49d8e7025a7e24a5011ed3b14445",
      "scenario/blender/runtime.py": "ba43726d16cd2de5cb08a26d96be9804f838e0fa4980f29501e6ce7e59719ad7",
      "scenario/blender/handlers.py": "950b2d28df02660b29a7523120addbf46583d9bc0b89efa06002f91c99312712"
    }
  }
}
---

# Shared cloud history recovery entry points

Evidence for [the canonical guide](../../UI_STYLE.md).
