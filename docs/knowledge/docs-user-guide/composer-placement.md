---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-placement",
  "title": "Floating composer drag edges and double-clicks",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-placement",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the floating composer guide sentences on dragging the pill and the card, the viewport, toolbar and sidebar edges they stop at, the card staying whole with its minus button and Generate in view, the background double-click reset and the prompt double-click word selection against the whole-composer clamp in composer_layout.py and the press pairing in modal.py and composer_layout.py, with the unit and installed native tests named in the UI style composer placement and double-click topics. Resizing, the remembered preferences and the other composer sentences keep their existing topics. No physical recheck of these sentences has been run since the change; physical acceptance stays under #66.",
    "sources": {
      "scenario/blender/composer/modal.py": "72554933af0043e7bc7a5e2a402f5720cc6ba6f28cd2420bca6cddbe55f2a8e4",
      "scenario/blender/composer/state.py": "b03073dc712fbb1a5386ba17b9d2c73c0bb6d7d91f2f79cd633a1218296da56f",
      "scenario/core/ui/composer_layout.py": "c624fa1cd59b3fa1180b5b4d5881bd32307744b3e6eb6496903d45b6ca87d66c",
      "tests/blender/test_composer.py": "8e90fb0fcc24aaba0ab68c25975e01b8e1a9f01e44bbfb6b048fd7069b79c9b9",
      "tests/unit/test_composer_layout.py": "97974826a4fd7502ff901e047c0bd38ca3740bcc762815db0bbfc95846dd4895"
    }
  }
}
---

# Floating composer drag edges and double-clicks

Evidence for [the canonical document](../../USER_GUIDE.md).
