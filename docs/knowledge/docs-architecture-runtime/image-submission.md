---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.image-submission",
  "title": "Shared Image quote and durable submission",
  "description": "Active Image UI and MCP submission through the selected JobSession.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "image-submission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected shared Image quote, exact approval, durable submission, polling, CDN transfer and original-origin packed PNG/OpenEXR delivery. Native synthetic tests cover UI/MCP parity, stale origins, failed transfers, multi-image rollback and receipt-only recovery. Other lanes, local-reference uploads, cancellation/restart/retry controls, physical input/focus and live paid/CDN acceptance remain outside this slice.",
    "sources": {
      "scenario/blender/model_jobs.py": "fe1fb51f47afd33c50ca3b1eacee539ccda395ca8ce2bb1f0f437ca1775c16a4",
      "scenario/blender/generation.py": "39205a8f8ac225801a11f5888b1394db77d3c8daa06e23ed0e392db2a7290857",
      "scenario/blender/runtime.py": "4b3b11aa9de9ea0eb2c347cb3d7532280dfa2633d5df5f21f8ad3ee5a02a3d21",
      "scenario/blender/job_session.py": "a2cff69015d295aa4ee11ce61d3a59cf9d188a1848fcd57e43594edfda7baa85",
      "scenario/mcp/tools_scenario.py": "22523ff549f48e9fede7f39be59b1cbadef5566e89be94ab7bf817d1cb7d2314",
      "scenario/core/jobs/coordinator.py": "b0d46de3342bc6e7afcb3acb4bde8fef8b07e6c5c502a4caa992a19b9560621c",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "tests/blender/test_model_generation.py": "ff8fc42cfb4683d3ea641622bbdb529d094960e29c2097a76660c86ff5bbea9b",
      "tests/blender/test_sdk_estimates.py": "31f5ab2037bb3b2f9ff1cb80207d0d2891bea9e84b931b994f68a19a7724e822",
      "tests/blender/test_session_results.py": "24ecda383518d81c3c42702054d196688e04da24c46b429f94cf99109c9efcbe",
      "scenario/core/scene/panorama.py": "e2d14956bb8240780919ae9f8824afc6bec4e1c62c222d0fe4d10276044f2fa8",
      "tests/unit/test_panorama.py": "f75277778003314b0e7b29a97e8547b3a2ddb1a2dfaf8148a3ab6edd53923950",
      "scenario/blender/image_application.py": "192c229312dc94f6362755859bdce9c940d88d38a7fdb3cf92ed3b57ef5d005e",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/jobs/transfers.py": "ca3aafdd915d908be78db5b0a7f3a535f0274e6f3ccc7e0cef7c2d88a90f212d",
      "scenario/core/jobs/results.py": "0ee36347a8c5be6ff84a36ae2dd54e9c64461de0a83bff513f29ac0bd7712889"
    }
  }
}
---

# Shared Image quote and durable submission

Evidence for [the canonical document](../../architecture/runtime.md).
