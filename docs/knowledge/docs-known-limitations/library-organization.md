---
{
  "type": "Evidence",
  "id": "docs-known-limitations.library-organization",
  "title": "Native Library organization limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed the Library organization bullet against the Library view, the shared request contract and adapter limits: one asset per native review while local MCP accepts up to 49, at most 200 collections loaded by Load collections and More (a collection created in the session joins beyond that), immediate metadata changes outside Blender Undo, no collection rename or deletion, model collections or tag listing, public pages disabled, session-local reviews lost on restart, file load or connection change while a sent write keeps its effect, verification by bulk read rather than search, an add of an asset already in the collection being refused as a whole and read back as verified without another request, as the service was observed to behave, and Japanese IME composition not starting in the dialog's Tags field on macOS, as in Blender's own text fields where pasting worked, with Apply, the card placement and the read-enabled controls still awaiting a desktop check. Rechecked after a settled card started keeping its outcome when another caller's prepare evicts its review, after a running page or collection read started keeping the read-back and after a ready card started naming an agent's change that holds the single apply: the bullet makes no claim about these cases, so it is unchanged. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. The latest installed run was on this branch on main 1d86f53d, after its restack onto the parent's collection page slot fix, which conflicted only in evidence records, and with the Library fixes that keep read-back on rows and collections a running read replaces and name an agent's change holding the single apply; their three new installed tests failed before those fixes. That full run's one other failure was the saved remote job action expectation that main corrected after this stack's base, and the run passed with main's corrected test file in place.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "9076253705e438782e59a79c489bcc5d24ca428fde2cc0a29612cd99ad25d2eb",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "scenario/core/ui/library_organization.py": "922eba9285e9794e3269dd60e7f28f6b2fe4dca334703dc2d7e2f42b55829e3c",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70",
      "tests/unit/test_library_organization.py": "798a3df61cb6c91af8c3e0cce2d957144b87ab9d92bd174bd4dc62383510a5d4",
      "tests/blender/run_all.py": "a3c22695eb7385958cc220fe7393e27a1fad92d135dc71a5d4c4279712c53b16",
      "scenario/core/api/sdk_adapter.py": "784ac9f7f7c071291086eef894a4bcb3d895e53b8b26a233efea2d119f395765",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e"
    }
  }
}
---

# Native Library organization limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md#interface-and-capture).
