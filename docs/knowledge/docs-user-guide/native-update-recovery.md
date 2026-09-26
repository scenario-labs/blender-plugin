---
{
  "type": "Evidence",
  "id": "docs-user-guide.native-update-recovery",
  "title": "Native update failure recovery",
  "description": "Recover disabled repositories and distinguish cached listings from successful refreshes.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "native-update-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "07ee22fb169cafa6a7b30fdcf8bc6bdd5773210c",
    "limits": "Inspected update operators and Blender repository UI sources. Exact main-source ZIP 821ce5760302e4bd89b57e0cb346671ca15906f0f6002b34646d45074d1b0195 was installed in disposable macOS arm64 profiles on Blender 5.0.1, 5.1.2 and 5.2.1. Loopback probes confirmed HTTP 404 retains the cached index and installed bytes, native filtering hides an entry requiring Blender 99, restored compatible metadata becomes visible, disabling the owning repository unregisters Scenario controls, and native re-enable preserves a seeded preference. Repeated setup creates no duplicate and checks download no additional ZIP. Final runs preserve normal profile metadata and remove disposable profiles. This is headless failure/recovery evidence, not desktop error presentation, published-release updates, all-state migration or other OS acceptance. The incompatible index was a synthetic metadata response; no incompatible archive was installed.",
    "sources": {
      "docs/USER_GUIDE.md": "b807a3b1e3e74c11b1ce44324af51923edf3ab5d5b04a014964e6e81c7430866",
      "scenario/blender/updates.py": "7391e0fd941bc24d8ddecc168d03858fad186a3f834c927c4ba92e2dae586862",
      "scenario/prefs.py": "52b84d7c54f32fc6540687815439a615117bb17a535de62ee665f8b3d0e98038",
      "tests/blender/test_updates.py": "2c4757ed88172dfde4e50c258ea3ba351ba65f26447d6b49ce07d36eae7daeae"
    }
  }
}
---

# Native update failure recovery

Evidence for [the user guide](../../USER_GUIDE.md#updates).
