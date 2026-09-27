---
{
  "type": "Evidence",
  "id": "docs-result-transfers.image-delivery",
  "title": "Active Image result delivery",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "image-delivery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected shared Image quotes, durable submission, result delivery and revision/context-bound UI/MCP saved-job controls. Native synthetic tests cover restart resume without import, failed-download retry, once-only cancellation, offline interrupted-download reconciliation, import receipt-only retry and responsive shared waits. Other lanes, local-reference uploads, explicit recovered-target application, physical input/focus and live paid/CDN acceptance remain incomplete. GUI controls were captured in an isolated profile; the interaction tool did not bind that window, so no native click proof is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "26e191b6482c6db6a0b6107d30c32ec6eb45606d1ba1a45c827eae849ff32d34",
      "scenario/blender/image_application.py": "192c229312dc94f6362755859bdce9c940d88d38a7fdb3cf92ed3b57ef5d005e",
      "scenario/blender/runtime.py": "59ce5120902fa6185d5558c1d33109c05507131bb5d1a3ee7e6727b6e955fc23",
      "scenario/blender/job_session.py": "a2cff69015d295aa4ee11ce61d3a59cf9d188a1848fcd57e43594edfda7baa85",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/scene/panorama.py": "e2d14956bb8240780919ae9f8824afc6bec4e1c62c222d0fe4d10276044f2fa8",
      "scenario/core/jobs/results.py": "0ee36347a8c5be6ff84a36ae2dd54e9c64461de0a83bff513f29ac0bd7712889",
      "scenario/core/jobs/transfers.py": "ca3aafdd915d908be78db5b0a7f3a535f0274e6f3ccc7e0cef7c2d88a90f212d",
      "scenario/mcp/tools_scenario.py": "d0376f05600f2d999f6fd5ed6cd7c0a50760309abb8445f9fd884cfdd5de8a50",
      "tests/blender/test_model_generation.py": "dffbae904c95734c6e693b051ca55b6e6c2cdaf246f67ebc4a258fd43c59caf5",
      "tests/blender/test_session_results.py": "24ecda383518d81c3c42702054d196688e04da24c46b429f94cf99109c9efcbe",
      "tests/unit/test_panorama.py": "f75277778003314b0e7b29a97e8547b3a2ddb1a2dfaf8148a3ab6edd53923950",
      "scenario/blender/job_recovery.py": "457cb3e24d41ed961f3bd794a48d082dba1e5df5044d592e69b4f2836912d9e7",
      "tests/unit/test_mcp_descriptions.py": "0e61e8472d2208010e0347b46b83b22c886560f339031c00cb04d036eff0f751",
      "scenario/blender/panels.py": "14bb6b4a109948238b0b94c74c432398d5f867663c6c550c03e28860fca16906",
      "tests/blender/test_mcp_contracts.py": "cb593c8b0b3939f172cb6e3217cd1f82b7f9ecb0fa7505c1295c38d88dcdbb83",
      "scenario/blender/registry.py": "1b7ce7233ee294f3cef4f0ead4c367f6da374cda26391a7bbda269771f9c08f4"
    }
  }
}
---

# Active Image result delivery

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
