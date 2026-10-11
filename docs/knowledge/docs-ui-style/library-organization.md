---
{
  "type": "Evidence",
  "id": "docs-ui-style.library-organization",
  "title": "Native Library collection and tag organization",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the Library organization section and its two pointers in the Explicit Studio view and Native Library controls sections against the Library view, the pure display module, the AssetOrganization owner and the runtime pump order: explicit collection reads (50 per page, at most 200, repeated cursors rejected), Browse setting the filter only in execute, row tag and membership summaries with +N counts, Refresh, Previous, Next, Load collections, More and Browse left enabled while their own read runs, with a second click refused and Previous, Next and More still following page availability, the Organize dialog fields and captured labels, the dynamic collection enum resolved through OperatorProperties, the dialog and dropdown asking to load collections before a load and, once a load finds none, saying the connection has none (Add suggests New collection and add, Remove has nothing to remove), inline validation before OK, prepare-only OK and cancel preparing nothing, one review card drawn under the organized asset's row with a pointing line under Previous and Next, or in that line's place when the shown page lacks the asset, and its phases, Apply gated on the shown READY review and single use, an asset added elsewhere before Apply reading back as Verified after one refused request with an already-in-the-collection note, read-back row updates and refresh marks for rows that left the browsed collection, a verified new collection joining the loaded list even at the 200-collection read bound, disabled public, loading and applying states, retirement on credential, Project ID or file change, the card surviving Studio redraws during Apply, sanitized refusals, online access off and the shared native and MCP owner, including its 32-review bound: when open agent reviews fill it, Organize reports that cause, keeps the card and prepares or sends nothing, and since a full bound evicts only settled reviews, a settled card keeps its outcome until dismissed after another caller's prepare evicts its review. The Blender 5.0 and 5.1 behavior behind the enabled controls was checked in Blender's public interface source for those release branches: a hovered button keeps its own disabled flag when the popup is rebuilt, and the 5.2 branch copies it from the rebuilt button; the pump already refreshes the Studio popup every tick. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths; they check what is drawn, not Blender's hover state. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No release acceptance is claimed.",
    "sources": {
      "docs/UI_STYLE.md": "4ede3b0591a3391e3b6901413152057c88f53cb45d21bf0dad1ed782d1a1efde",
      "scenario/blender/library_view.py": "c6edd4e8d63907cb7cbb36fde39963b38844b40e9dbc5f21de99381cd0cfc5a3",
      "scenario/core/ui/library_organization.py": "e6e3b208a4cb375412fc73779ed15ae56c9e9ea63d883a90d5ec54f6d868def4",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "33461ba284a3b85282784f699e249a66df2f2503a55ad2acdda8756602957cae",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "100262ba2e1c546fba06d25e06c6f6b778eb90cf0a01bf73447cb91f908834a6",
      "tests/unit/test_library_organization.py": "d820a1028a2ec18e8da636708e1c02618a006d47f5838c77a07e85dcc6b0be89",
      "tests/blender/run_all.py": "f32e42a29f8c0403f6f1524d17fc3e020cb44ee4ec0173fe657c3ff609a74bba",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071"
    }
  }
}
---

# Native Library collection and tag organization

Evidence for [the canonical guide](../../UI_STYLE.md#library-organization).
