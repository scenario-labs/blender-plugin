---
{
  "type": "Evidence",
  "id": "docs-mcp.media-reference-uploads",
  "title": "Typed local media reference uploads",
  "description": "Explicit upload kinds and persisted metadata through the shared session and local MCP.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "media-reference-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "29abc71f35c858af941328e02282aaaa865e595a",
    "limits": "Reviewed explicit image/audio/video/3d filename and MIME admission, default-image compatibility, persisted metadata returned by MCP status/recovery, and reuse of SDK 2.2.0 upload methods without an adapter or dependency change. Native tests use synthetic bytes and mocked transport to cover exact SDK metadata, immutable staging, rejected kinds/extensions, remote metadata mismatch, uncertain initialization without replay, restart and cleanup. This establishes transport and lifecycle behavior, not media decoding, live API/provider format acceptance, non-image UI preparation, sidecar discovery, paid generation or complete issue acceptance.",
    "sources": {
      "scenario/blender/reference_uploads.py": "be3455c20dcff30e44dc6e984c66cd31f7664db1ee095ad3917956e3ce90bac4",
      "scenario/blender/job_session.py": "6df07b116f3eea2efb46a6cfe2f60025ec3a0ba821119c181378f14e26dd7ab8",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "scenario/core/jobs/uploads.py": "fee6cebbb4cf6b8390b788a053fa9ba882f512182c40216f0656670c0319604d",
      "scenario/core/jobs/upload_sources.py": "2fc272529cc87abb0809e17b12792136d617632721b40df2e7b6d3b81fa7664b",
      "scenario/mcp/tools_scenario.py": "dab58d2abd0b1753eca90789badb00fdb0287fd97e380c4945a39a0998b83bb0",
      "tests/blender/test_reference_uploads.py": "39dd04c63e642cc19ed25c199682881366a6b1661304f5a6e29cd2f73033600b",
      "tests/blender/test_session_uploads.py": "c51bc1488c072f02b6523f9ccc9f1efadfebca18c1ad94afae690dd4237f25f3",
      "tests/unit/test_mcp_descriptions.py": "104a3278279beb2ee40e761da71d23410c721998f707e8c822572f9ee46001bf"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
