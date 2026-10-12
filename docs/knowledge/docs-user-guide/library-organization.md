---
{
  "type": "Evidence",
  "id": "docs-user-guide.library-organization",
  "title": "Organizing Library assets from Studio",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed the Organize Library assets section and the edited closing sentence of Browse Library assets against the Library view, the pure display module and the shared review owner: tag and membership display, Load collections and More (50 per read, up to 200), Browse, the five Organize actions, the dialog saying when Load collections found none and pointing to New collection and add, OK preparing a review without sending, the review card opening under the asset's row with a line near the top pointing to it, Apply once, Discard, the 10-minute expiry, the read-back outcome labels, the card showing Verified and that the asset was already in the collection when another client added it after the review, the no-credit and no-undo notice, unconfirmed guidance without automatic resend, refresh marks, a page or collection list that was loading when the result arrived keeping it, disabled states, Refresh, Next, Previous, Load collections, More and Browse staying available while their read runs with a second click only reported, a new review replacing a card that is not applying, closing Studio during Apply, clearing on credential, Project ID or file change, online access off, the one-change limit shared with local MCP, with a ready card saying when an agent's change is being applied and Apply sending nothing until it finishes, and Organize explaining, without preparing or sending anything, when an agent's open reviews fill the shared bound until they are applied, discarded or expire; a settled card keeping its outcome after another caller's prepare evicts its review needs no user action and is not described. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. The latest installed run was on this branch on main 1d86f53d, after its restack onto the parent's collection page slot fix, which conflicted only in evidence records, and with the Library fixes that keep read-back on rows and collections a running read replaces and name an agent's change holding the single apply; their three new installed tests failed before those fixes. That full run's one other failure was the saved remote job action expectation that main corrected after this stack's base, and the run passed with main's corrected test file in place.",
    "sources": {
      "docs/USER_GUIDE.md": "e76e95c51be2c93d3f4b20fe268ab67e7de8fe87bb70aa889ce23cc0982b1670",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "scenario/core/ui/library_organization.py": "922eba9285e9794e3269dd60e7f28f6b2fe4dca334703dc2d7e2f42b55829e3c",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70",
      "tests/unit/test_library_organization.py": "798a3df61cb6c91af8c3e0cce2d957144b87ab9d92bd174bd4dc62383510a5d4",
      "tests/blender/run_all.py": "a3c22695eb7385958cc220fe7393e27a1fad92d135dc71a5d4c4279712c53b16"
    }
  }
}
---

# Organizing Library assets from Studio

Evidence for [the canonical guide](../../USER_GUIDE.md#organize-library-assets).
