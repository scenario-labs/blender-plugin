---
{
  "type": "Evidence",
  "id": "docs-user-guide.library-organization",
  "title": "Organizing Library assets from Studio",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed on 2026-10-13 against the rewritten Organize Library assets section. Checked in code: Organize offers Add to collection, Remove from collection, Add tags, Remove tags and New collection and add, which creates the collection and then adds the asset; OK reads the current state into a review card and sends nothing; Apply sends a ready review once, and a review expires 10 minutes after it becomes ready; the card reports the read-back result, with per-asset labels Verified, Refused (with the HTTP status), Unconfirmed, Not sent and Not verified, or says the outcome is unknown; an uncertain write stops later writes and is never sent again, and the card says to refresh and inspect, with nothing resent automatically (the only resend is the bounded add retry, during Apply, for assets read back as not yet members after a refusal that wrote nothing); the notice says changes are immediate account metadata, use no credits and are not reversed by Blender Undo; Library offers no collection rename or delete. Sources read: library_view (dialog, apply, discard, card), core/ui/library_organization (actions, labels, card lines), asset_organization (shared owner, closed with its session), core/jobs/organization (review lifetime, single apply, write guard, verification) and runtime (pump order and retirement). Offline unit tests tests/unit/test_library_organization.py, test_asset_organization.py and test_sdk_adapter_organization.py passed with test_asset_library.py (440). The native tests in tests/blender/test_library_organization.py were read, not run; earlier installed-ZIP results and the earlier read-only desktop pass predate these sources and are not relied on. Not verified here: installed runs of this code on Blender 5.0, 5.1 or 5.2, Apply and dialog interaction on a desktop, other operating systems and DPI (#66), live collection or tag writes, service name uniqueness, tag normalization and live limits, and collection rename or delete in Scenario's web app. No live write or spending. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "5a627dd3a18d30092ce168797c91e1e971c4bd5f27d955f55fb91a10eb7e338d",
      "scenario/blender/library_view.py": "b6a0757506308b0a106a914389d6a25fad9533bc132018e5b904f183c4633737",
      "scenario/core/ui/library_organization.py": "922eba9285e9794e3269dd60e7f28f6b2fe4dca334703dc2d7e2f42b55829e3c",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/runtime.py": "c8303eead552a5de421c69c56cb754c2d463f117909b46273c791d46275eb707",
      "scenario/core/jobs/organization.py": "64c7cc990c8720827769d8d4ef0adc4715dfd2893c776c15639b7a5a85d186f3",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70",
      "tests/unit/test_library_organization.py": "798a3df61cb6c91af8c3e0cce2d957144b87ab9d92bd174bd4dc62383510a5d4",
      "tests/unit/test_asset_organization.py": "095cea215498e2e6ca6ba987ed06b7bcfd2a877a0d0c475463c9b9cb4f3f7a93",
      "tests/blender/run_all.py": "bcce33605252d54bbc0e78e45f0806809c9ec1b515b0c0fe0e97f0a4372b0944"
    }
  }
}
---

# Organizing Library assets from Studio

Evidence for [the canonical guide](../../USER_GUIDE.md#organize-library-assets).
