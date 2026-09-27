---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.image-submission",
  "title": "Shared Image quote and durable submission",
  "description": "Active Image UI and MCP submission through the selected JobSession.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "image-submission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected shared Image quotes, durable submission, delivery and revision/context-bound UI/MCP recovery. Native synthetic tests cover explicit destination approval after restart, scene/context invalidation before and after verification, single-use import, receipt-only retry, download/cancellation recovery and responsive waits. Schema 2-to-3 upgrade and destination claim failure/race cases have offline unit coverage. The exact ZIP passed 460 native tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS ARM64. The native import confirmation was captured and visually inspected in an isolated offline profile; it performed no import before approval. Physical input/focus remain unverified because the interaction tool selected a different window. Other lanes, local-reference uploads and live paid/CDN acceptance remain incomplete.",
    "sources": {
      "scenario/blender/model_jobs.py": "c5f0b39503980449f03ba88d2061a3ed3a774d76a4399f8c03c87d49249465c2",
      "scenario/blender/generation.py": "39205a8f8ac225801a11f5888b1394db77d3c8daa06e23ed0e392db2a7290857",
      "scenario/blender/runtime.py": "004d37f64b16feb6d6719ca605f362b227db4844a684c915265c3d45d3045418",
      "scenario/blender/job_session.py": "ae74304a63af786b97952f09a0ce0d2bfc005cb6cf19de823ddc9d949867a9dd",
      "scenario/mcp/tools_scenario.py": "72711861ef93c4ee37c5d740c4bde409f8fcc6c951db0d462d5c5ce2ca815130",
      "scenario/core/jobs/coordinator.py": "fc489afa1753dc08be2eb9cd4202fdb1b51cbf62214daf368f04907d3ee55eab",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "tests/blender/test_model_generation.py": "3c782118573cb4f6bece2bc7311f88a0abe922483297dae600ec8cf33f1a23cb",
      "tests/blender/test_sdk_estimates.py": "31f5ab2037bb3b2f9ff1cb80207d0d2891bea9e84b931b994f68a19a7724e822",
      "tests/blender/test_session_results.py": "24ecda383518d81c3c42702054d196688e04da24c46b429f94cf99109c9efcbe",
      "scenario/core/scene/panorama.py": "e2d14956bb8240780919ae9f8824afc6bec4e1c62c222d0fe4d10276044f2fa8",
      "tests/unit/test_panorama.py": "f75277778003314b0e7b29a97e8547b3a2ddb1a2dfaf8148a3ab6edd53923950",
      "scenario/blender/image_application.py": "192c229312dc94f6362755859bdce9c940d88d38a7fdb3cf92ed3b57ef5d005e",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/jobs/transfers.py": "ca3aafdd915d908be78db5b0a7f3a535f0274e6f3ccc7e0cef7c2d88a90f212d",
      "scenario/core/jobs/results.py": "0ee36347a8c5be6ff84a36ae2dd54e9c64461de0a83bff513f29ac0bd7712889",
      "scenario/blender/job_recovery.py": "5e0115967ce0af4cd525c2ffa131ca0ffab907a9b7cf708538028acc73e2919e",
      "tests/unit/test_mcp_descriptions.py": "af0d01bc2919e62f4eaf5c67a1eb1b5b14c6a690ff79cab92d71a44fd7171c2e",
      "scenario/blender/panels.py": "14bb6b4a109948238b0b94c74c432398d5f867663c6c550c03e28860fca16906",
      "tests/blender/test_mcp_contracts.py": "96265c1749b6b93f7cd02a4369028dd17f3bb0319645bc1e90ad31e735febf81",
      "scenario/blender/registry.py": "1b7ce7233ee294f3cef4f0ead4c367f6da374cda26391a7bbda269771f9c08f4",
      "scenario/core/jobs/store.py": "ea0178a71eafdc44a1b06df4ebd8f310a5760ee311d4a95c0e19ba71f02bf3de",
      "tests/unit/test_job_store.py": "10bca4dc8cfe918d47e17a6550d0733ee88a3b776a9b72d5ca89e77e6a1b15d5",
      "tests/unit/test_application_claims.py": "d80595586f743b25f9e2fc8c388f6b6456a96044d074ee760c9087f084076d63"
    }
  }
}
---

# Shared Image quote and durable submission

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
