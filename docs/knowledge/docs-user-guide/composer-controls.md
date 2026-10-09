---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-controls",
  "title": "Floating composer Settings route and collapse behavior",
  "description": "3D Edit mode reached through the composer Settings dialog; only the minus button collapses the card.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the floating composer's sidebar-only lanes, 3D Edit route and collapse sentences against source. The composer tabs cover six generation lanes; its Settings chip opens the lane form dialog, whose 3D form includes the Text, Image, Multi-view and Edit mode selector and the Edit form. Only the minus button clears the expanded state; a click outside the card commits a focused prompt to its lane and passes the click through without collapsing it. Installed native tests in tests/blender/test_studio_view.py drive the composer modal with synthetic outside-click events: a focused prompt is committed to its lane and the click passes through, a changed prompt, lane or scene is rejected before the handoff, and an unfocused click commits no stale text. They do not assert that the card stays expanded and are not physical input proof. Documentation-only review: no native, desktop or physical input run for this change, and Edit 3D Generate readiness from the composer was not reviewed. Other composer claims keep the inherited composer topic limits.",
    "sources": {
      "scenario/blender/composer/modal.py": "362aa797f4f52a8e8e320a024f64bd187eab39cdc32fbc8f26c03d4d168daebb",
      "scenario/blender/composer/state.py": "063ea956a996356b7dd1b28cc16b7dc4aaa1806a9336efe7d0d79052afbf5f79",
      "scenario/core/ui/composer_layout.py": "ec5a7e92e881a9c356f1a20619170b1cf4f2a930db15dbe057e5bead2d11453a",
      "scenario/blender/operators.py": "8fb3a35beb010e81f4d4eaecf22688d8baf051ad88cdf2def50664e0da01a103",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/blender/props.py": "f33955bbca26a36c8439ea3d57b2ef75110947ac8605cd21c2e903dac60d3bdb",
      "tests/blender/test_composer.py": "0471897849f2d38c49eb7496cecfc2eb52bdb4ec1517902cdc712dd10b28824c",
      "tests/blender/test_studio_view.py": "e33f0e44cbe75cabdfa38ecd68ca991e010a4e0322803813f3464b2c9e9f7e78"
    }
  }
}
---

# Floating composer Settings route and collapse behavior

Evidence for [the canonical document](../../USER_GUIDE.md).
