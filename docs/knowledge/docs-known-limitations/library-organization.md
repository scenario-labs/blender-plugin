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
    "base_revision": "ff8d29d879487719fde8fd9b4089438ae0ba2c78",
    "limits": "Reviewed the Library organization bullet against the Library view, the shared request contract and adapter limits: one asset per native review while local MCP accepts up to 49, at most 200 collections loaded by Load collections and More (a collection created in the session joins beyond that), immediate metadata changes outside Blender Undo, no collection rename or deletion, model collections or tag listing, public pages disabled, session-local reviews lost on restart, file load or connection change while a sent write keeps its effect, verification by bulk read rather than search, an add of an asset already in the collection being refused as a whole and read back as verified without another request, as the service was observed to behave, and Japanese IME composition not starting in the dialog's Tags field on macOS, as in Blender's own text fields where pasting worked, with Apply, the card placement and the read-enabled controls still awaiting a desktop check. Rechecked after a settled card started keeping its outcome when another caller's prepare evicts its review, after a running page or collection read started keeping the read-back and after a ready card started naming an agent's change that holds the single apply: the bullet makes no claim about these cases, so it is unchanged. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. The latest installed run was on this branch on main 3acb9625, after its restack onto the parent's rebase over the local Film export owner, which conflicted only in evidence records; the full run passed. The three installed tests for the Library fixes that keep read-back on rows and collections a running read replaces and name an agent's change holding the single apply failed before those fixes. On 2026-10-12 the run_all.py fingerprint was refreshed after the saved model package import was rebuilt on this change; it only adds test_model_packages to the native baseline beside test_library_organization, so these claims are unchanged. The review date is unchanged. On 2026-10-12 the run_all.py fingerprint was refreshed again after saved splat import added test_splat_application to the native baseline; these claims are unchanged, as is the review date. Rechecked on 2026-10-12 against private live and desktop reports, without new runs: on 2026-10-10 a free live run on a pre-merge #380 head applied and independently read back one asset's collection add and removal and tag additions and removals through local MCP and the native operators in background Blender 5.1.2, then restored the asset; SDKAdapter.remove_collection_assets sends the IDs as a DELETE JSON body, so that one-asset removal's body reached the service. The already-member refusal, name uniqueness on the service, tag normalization and limits were not exercised. A read-only physical desktop pass on macOS arm64 Blender 5.1.2 at UI scales 1.0 and 2.0 checked card placement and read-enabled controls after fixes; at 2.0 only the card header shows at the bottom of the Studio popup until scrolled. Apply was not exercised on a desktop. Sources changed by later pull requests (runtime.py, organization.py, run_all.py, tools_scenario.py) were not re-reviewed. On 2026-10-13 the KNOWN_LIMITATIONS.md fingerprint was refreshed after the Library organization bullet was re-read against these limits; the other sources and the review date are unchanged.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "2c03725d4ec3874f82f692472fa34b5b7ed14b75314333ba25e9fc5dfcb7d390",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "scenario/core/ui/library_organization.py": "922eba9285e9794e3269dd60e7f28f6b2fe4dca334703dc2d7e2f42b55829e3c",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/runtime.py": "5ff43fb59215fed469c0638a660a679a6c15fd63a0148169031e01a4b6dfcfd7",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70",
      "tests/unit/test_library_organization.py": "798a3df61cb6c91af8c3e0cce2d957144b87ab9d92bd174bd4dc62383510a5d4",
      "tests/blender/run_all.py": "0d391268d1c8d0f140aa30cd61b9e901e3d7c531dde0c3ead2e6be635fea0cca",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "scenario/mcp/tools_scenario.py": "c3597642a8199cde05d1346120532681f7138572e3edf523fa3788489b5f3b3c"
    }
  }
}
---

# Native Library organization limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md#interface-and-capture).
