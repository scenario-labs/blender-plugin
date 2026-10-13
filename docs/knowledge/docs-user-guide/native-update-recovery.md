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
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "2026-10-13: reviewed the current guide's Updates text: panel location and status, the Set up official repository, Check for updates and Open Get Extensions buttons, Allow Online Access, failed-check and restart advice, in-place repository updates, ZIP copies, and recovery after disabling Scenario's repository. Checked against scenario/blender/updates.py and scenario/prefs.py, which draws the Updates box at the end of Scenario's add-on preferences. Setup and check need Allow Online Access; setup reuses or re-enables an existing official repository and never adds a second one; check syncs only that repository and installs nothing; once that repository exists, a copy from another repository is told it was installed outside it. The panel shows Set up official repository only while the repository is missing or disabled and Check for updates otherwise, so the guide's button list was reported for clarification. The Update guide button opens https://blender.scenario.com/#updates; the guide's Updates heading renders with the id updates under the site's Markdown toc settings. tests/blender/test_updates.py and tests/blender/test_desktop_open.py (preference links, including that anchor) were read, not run; no offline unit test covers these claims. For the Blender-side claims, Blender 5.0.1's bundled extension manager source was read: listings skip entries incompatible with the Blender version or platform; an update keeps the add-on's preferences entry and does not touch its user directory, while uninstall removes both. Earlier (2026-09-26): exact main-source ZIP 821ce5760302e4bd89b57e0cb346671ca15906f0f6002b34646d45074d1b0195 in disposable macOS arm64 profiles on Blender 5.0.1, 5.1.2 and 5.2.1, with loopback probes: HTTP 404 kept the cached index and installed bytes, native filtering hid an entry requiring Blender 99, restored compatible metadata became visible, disabling the owning repository unregistered Scenario's controls and native re-enable preserved a seeded preference; repeated setup created no duplicate and checks downloaded no additional ZIP. The incompatible index was synthetic metadata; no incompatible archive was installed. The update operators and panel logic are unchanged since then apart from the link buttons moving to scenario.open_url. Not verified: desktop error presentation in Get Extensions, an update between two published releases keeping preferences and jobs, Windows and Linux. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "5a627dd3a18d30092ce168797c91e1e971c4bd5f27d955f55fb91a10eb7e338d",
      "scenario/blender/updates.py": "6678248428a6785dd0a2c0ba042338ee493c3a5da26f6471fc9fc3ad904d52b7",
      "scenario/prefs.py": "8501a51e598083a7414aa1c55c599001747e60caf57a0ce859402422880cf762",
      "tests/blender/test_updates.py": "2c4757ed88172dfde4e50c258ea3ba351ba65f26447d6b49ce07d36eae7daeae",
      "tests/blender/test_desktop_open.py": "9605dbcdf6bae02090de3dc3555b3f7cd30ec48e6f044f060d93a4149b11dcdb"
    }
  }
}
---

# Native update failure recovery

Evidence for [the user guide](../../USER_GUIDE.md#updates).
