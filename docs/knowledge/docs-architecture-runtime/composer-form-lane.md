---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.composer-form-lane",
  "title": "Shared Edit 3D form lane rule",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the shared lane rule and its callers: the pricing pump's visible lane, the composer state, draw and modal handler, the sidebar Edit form's Generate row and the Generate operator. Lane-bound quote validation and durable submission in generation.py and model_jobs.py are unchanged. Installed offline tests on Blender 5.1.2 macOS arm64 cover the Edit quote being consumed by the composer while a ready 3D-tab quote is left untouched, and no request when only the 3D-tab price is ready. No live provider pricing, desktop interaction or release acceptance is claimed.",
    "sources": {
      "scenario/blender/props.py": "511b333e2bb5359235ab6883ed232e55048eb91e740b1db675e9e37e930ea5a8",
      "scenario/blender/operators.py": "f59b9ccd5295e9f2bbac08ad883bd549f52c113142d7f3d22cd45a8e3ff1f87c",
      "scenario/blender/panels.py": "483c4334ca74eb40a753115180ea082ee731ae4bf430d35563d8ef5dbb4651bb",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/blender/composer/state.py": "4eb460283dba15ed11654dca107688490e75c70ca65b0a4aee060e2410282603",
      "scenario/blender/composer/draw.py": "ef2815fc1b2aa352abea72950ebc4861c69e0dcb3e25f11d5f6cd1c91e4046b5",
      "scenario/blender/composer/modal.py": "4aaac614b5d5787eb5c0f05e966cbe23a4a2691e675a2f15669ceab687aa2701",
      "tests/blender/test_composer.py": "b2d642f835d752dabd0fb1f77c3bdb3e3b3332e127eace0201ba6ad26a1c305b"
    }
  }
}
---

# Shared Edit 3D form lane rule

Evidence for the [canonical guide](../../architecture/runtime.md).
