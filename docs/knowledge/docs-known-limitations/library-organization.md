---
{
  "type": "Evidence",
  "id": "docs-known-limitations.library-organization",
  "title": "Native Library organization limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Library organization bullet against the Library view, the shared request contract and adapter limits: one asset per native review while local MCP accepts up to 49, at most 200 loaded collections, immediate metadata changes outside Blender Undo, no collection rename or deletion, model collections or tag listing, public pages disabled, session-local reviews lost on restart, file load or connection change while a sent write keeps its effect, and verification by bulk read rather than search. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. No physical desktop input, focus, typing, Unicode or IME composition, Escape, viewport, small-window or alternate-DPI evidence and no screenshots exist for these controls; that evidence is pending under #66 and will be collected later in an unlocked session. No live collection, tag or bulk request was made; service name uniqueness, re-adding a member, DELETE body survival, tag normalization and live limits remain unverified.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "759d05296a72009261e1a12f09bdf1c86cf5a30fbfdc1846fc0aa888f968ec37",
      "scenario/blender/library_view.py": "f2b832b67d2eb388901782f45621e49c009d3fa40e876c5b4ad4f35a98449555",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "9468693ddd2941575470018633b425885401ae68551c89fc88773ef0fce20933",
      "scenario/core/jobs/organization.py": "7f69ce28e4c54e3c2b819cc76735d001671de6bcfcb12145b2cd90b059e8b84d",
      "tests/blender/test_library_organization.py": "54d7098acbae666f86ff0d14eb6a568da0af6972a1eb733b0cc6678c30a1f6a4",
      "tests/unit/test_library_organization.py": "5795cb464357418efa275114ecf0846a55b9dd102e9d2cd3cf4d1fa97dc90f16",
      "tests/blender/run_all.py": "b3019328085a8334dd3347248a9b145d3a23533ffbafcfac9304962df189a6c8",
      "scenario/core/api/sdk_adapter.py": "8741ed98d0d4ace8a4d1c21a65aaf79f85eeabf69023477d23fa028f4911bb95",
      "scenario/mcp/tools_scenario.py": "79d6bfc51b06fba53b870739220068822ae4df0aac3c45d4d68b755794d34356"
    }
  }
}
---

# Native Library organization limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md#interface-and-capture).
