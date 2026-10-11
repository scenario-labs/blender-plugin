---
{
  "type": "Evidence",
  "id": "docs-user-guide.library-organization",
  "title": "Organizing Library assets from Studio",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed the Organize Library assets section and the edited closing sentence of Browse Library assets against the Library view, the pure display module and the shared review owner: tag and membership display, Load collections and More (50 per read, up to 200), Browse, the five Organize actions, the dialog saying when Load collections found none and pointing to New collection and add, OK preparing a review without sending, the review card opening under the asset's row with a line near the top pointing to it, Apply once, Discard, the 10-minute expiry, the read-back outcome labels, the card showing Verified and that the asset was already in the collection when another client added it after the review, the no-credit and no-undo notice, unconfirmed guidance without automatic resend, refresh marks, disabled states, Refresh, Next, Previous, Load collections, More and Browse staying available while their read runs with a second click only reported, a new review replacing a card that is not applying, closing Studio during Apply, clearing on credential, Project ID or file change, online access off, the one-change limit shared with local MCP, and Organize explaining, without preparing or sending anything, when an agent's open reviews fill the shared bound until they are applied, discarded or expire; a settled card keeping its outcome after another caller's prepare evicts its review needs no user action and is not described. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. Rechecked after a restack onto the MCP branch's rebase onto main 7fb15252, which conflicted only in evidence records: main's merged changes to the user guide, the runtime pump and the installed test list leave this section and the Browse Library assets sentence unchanged. The installed tests last ran on this branch before that restack; only the unit suite ran locally after it.",
    "sources": {
      "docs/USER_GUIDE.md": "18aa2d441edc9d525c9637d6d31e1ae6a3a84801f5b65c322cfee3e18d3a5502",
      "scenario/blender/library_view.py": "c6edd4e8d63907cb7cbb36fde39963b38844b40e9dbc5f21de99381cd0cfc5a3",
      "scenario/core/ui/library_organization.py": "e6e3b208a4cb375412fc73779ed15ae56c9e9ea63d883a90d5ec54f6d868def4",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "100262ba2e1c546fba06d25e06c6f6b778eb90cf0a01bf73447cb91f908834a6",
      "tests/unit/test_library_organization.py": "d820a1028a2ec18e8da636708e1c02618a006d47f5838c77a07e85dcc6b0be89",
      "tests/blender/run_all.py": "a3c22695eb7385958cc220fe7393e27a1fad92d135dc71a5d4c4279712c53b16"
    }
  }
}
---

# Organizing Library assets from Studio

Evidence for [the canonical guide](../../USER_GUIDE.md#organize-library-assets).
