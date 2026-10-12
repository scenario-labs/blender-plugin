---
{
  "type": "Evidence",
  "id": "docs-ui-style.library-organization",
  "title": "Native Library collection and tag organization",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "3acb9625dc28bc74a6b764163ce6a6ca27144528",
    "limits": "Reviewed the Library organization section and its two pointers in the Explicit Studio view and Native Library controls sections against the Library view, the pure display module, the AssetOrganization owner and the runtime pump order: explicit collection reads (50 per page, at most 200, repeated cursors rejected), Browse setting the filter only in execute, row tag and membership summaries with +N counts, Refresh, Previous, Next, Load collections, More and Browse left enabled while their own read runs, with a second click refused and Previous, Next and More still following page availability, the Organize dialog fields and captured labels, the dynamic collection enum resolved through OperatorProperties, the dialog and dropdown asking to load collections before a load and, once a load finds none, saying the connection has none (Add suggests New collection and add, Remove has nothing to remove), inline validation before OK, prepare-only OK and cancel preparing nothing, one review card drawn under the organized asset's row with a pointing line under Previous and Next, or in that line's place when the shown page lacks the asset, and its phases, Apply gated on the shown READY review and single use, an asset added elsewhere before Apply reading back as Verified after one refused request with an already-in-the-collection note, read-back row updates and refresh marks for rows that left the browsed collection, a verified new collection joining the loaded list even at the 200-collection read bound, a page or collection read already running when the read-back arrives keeping it on its rows and in the collection list, the next read showing what Scenario lists, disabled public, loading and applying states, retirement on credential, Project ID or file change, the card surviving Studio redraws during Apply, sanitized refusals, online access off and the shared native and MCP owner, including its 32-review bound: when open agent reviews fill it, Organize reports that cause, keeps the card and prepares or sends nothing, and since a full bound evicts only settled reviews, a settled card keeps its outcome until dismissed after another caller's prepare evicts its review; while an agent's change holds the owner's single apply, a ready card says so and Apply stays offered but refuses with that reason and sends nothing. The Blender 5.0 and 5.1 behavior behind the enabled controls was checked in Blender's public interface source for those release branches: a hovered button keeps its own disabled flag when the popup is rebuilt, and the 5.2 branch copies it from the rebuilt button; the pump already refreshes the Studio popup every tick. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths; they check what is drawn, not Blender's hover state. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No release acceptance is claimed. The latest installed run was on this branch on main 3acb9625, after its restack onto the parent's rebase over the local Film export owner, which conflicted only in evidence records; the full run passed. The three installed tests for the Library fixes that keep read-back on rows and collections a running read replaces and name an agent's change holding the single apply failed before those fixes.",
    "sources": {
      "docs/UI_STYLE.md": "3411acff6c8d9709f596c1a371d32d8e870bcd2267602a92bb6ec303877ed8d5",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "scenario/core/ui/library_organization.py": "922eba9285e9794e3269dd60e7f28f6b2fe4dca334703dc2d7e2f42b55829e3c",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/runtime.py": "5ff43fb59215fed469c0638a660a679a6c15fd63a0148169031e01a4b6dfcfd7",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70",
      "tests/unit/test_library_organization.py": "798a3df61cb6c91af8c3e0cce2d957144b87ab9d92bd174bd4dc62383510a5d4",
      "tests/blender/run_all.py": "808c5fc5fa9fe528c1bceb709b527834107e0ebc9dc587df6cb262a558b35b34",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071"
    }
  }
}
---

# Native Library collection and tag organization

Evidence for [the canonical guide](../../UI_STYLE.md#library-organization).
