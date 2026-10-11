---
{
  "type": "Evidence",
  "id": "docs-known-limitations.library-organization",
  "title": "Native Library organization limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the Library organization bullet against the Library view, the shared request contract and adapter limits: one asset per native review while local MCP accepts up to 49, at most 200 collections loaded by Load collections and More (a collection created in the session joins beyond that), immediate metadata changes outside Blender Undo, no collection rename or deletion, model collections or tag listing, public pages disabled, session-local reviews lost on restart, file load or connection change while a sent write keeps its effect, verification by bulk read rather than search, and an add of an asset already in the collection being refused as a whole and read back as verified without another request, as the service was observed to behave. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. No physical desktop input, focus, typing, Unicode or IME composition, Escape, viewport, small-window or alternate-DPI evidence and no screenshots exist for these controls; that evidence is pending under #66 and will be collected later in an unlocked session. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "791ced4e43457d2d0a4209311cdf0b517c9c4ef2e88df2ded5f5323a09bde53a",
      "scenario/blender/library_view.py": "9d64adaa197fc1d212c95b3b256d61ff67acdc9456ef1266c61c3168b2c50f17",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "33461ba284a3b85282784f699e249a66df2f2503a55ad2acdda8756602957cae",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "6da76fcae49830a07389f77dba025ce17fa5ae2750995bd52c94d90927579d7d",
      "tests/unit/test_library_organization.py": "5795cb464357418efa275114ecf0846a55b9dd102e9d2cd3cf4d1fa97dc90f16",
      "tests/blender/run_all.py": "f32e42a29f8c0403f6f1524d17fc3e020cb44ee4ec0173fe657c3ff609a74bba",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "scenario/mcp/tools_scenario.py": "6e4a3b38ae75521eea54daed93e2a8612dbf49b33eea8de968d084fd84260c99"
    }
  }
}
---

# Native Library organization limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md#interface-and-capture).
