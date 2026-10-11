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
    "limits": "Reviewed the Library organization bullet against the Library view, the shared request contract and adapter limits: one asset per native review while local MCP accepts up to 49, at most 200 collections loaded by Load collections and More (a collection created in the session joins beyond that), immediate metadata changes outside Blender Undo, no collection rename or deletion, model collections or tag listing, public pages disabled, session-local reviews lost on restart, file load or connection change while a sent write keeps its effect, verification by bulk read rather than search, an add of an asset already in the collection being refused as a whole and read back as verified without another request, as the service was observed to behave, and Japanese IME composition not starting in the dialog's Tags field on macOS, as in Blender's own text fields where pasting worked, with Apply, the card placement and the read-enabled controls still awaiting a desktop check. Rechecked after a settled card started keeping its outcome when another caller's prepare evicts its review: the bullet makes no claim about that case, so it is unchanged. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "96cbc8df446f6bfb7f2d8a9cdfa32a10a0713e1763d1dc621535c89e4959358c",
      "scenario/blender/library_view.py": "c6edd4e8d63907cb7cbb36fde39963b38844b40e9dbc5f21de99381cd0cfc5a3",
      "scenario/core/ui/library_organization.py": "e6e3b208a4cb375412fc73779ed15ae56c9e9ea63d883a90d5ec54f6d868def4",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "33461ba284a3b85282784f699e249a66df2f2503a55ad2acdda8756602957cae",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "100262ba2e1c546fba06d25e06c6f6b778eb90cf0a01bf73447cb91f908834a6",
      "tests/unit/test_library_organization.py": "d820a1028a2ec18e8da636708e1c02618a006d47f5838c77a07e85dcc6b0be89",
      "tests/blender/run_all.py": "f32e42a29f8c0403f6f1524d17fc3e020cb44ee4ec0173fe657c3ff609a74bba",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "scenario/mcp/tools_scenario.py": "6e4a3b38ae75521eea54daed93e2a8612dbf49b33eea8de968d084fd84260c99"
    }
  }
}
---

# Native Library organization limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md#interface-and-capture).
