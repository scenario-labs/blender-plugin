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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the shared lane rule and its callers: the pricing pump's visible lane, the sidebar and Settings form choice, the composer state, draw and modal handler and the Generate operator, plus the model picker's model-to-form mapping and the composer's commit guard, including its lane tab and double-click paths. Lane-bound quote validation and durable submission in generation.py and model_jobs.py are unchanged. Installed offline tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the Edit quote being consumed by the composer while a ready 3D-tab quote is left untouched, no request when only the 3D-tab price is ready, and no write or request after the form behind a focused prompt changed, including after a lane tab or a double-click. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's prepared job cancellation, experimental status, Codex token and handbook changes: the model picker only gains a read-only experimental status label, so the model-to-form mapping is unchanged. No live provider pricing, physical desktop input or release acceptance is claimed.",
    "sources": {
      "scenario/blender/props.py": "46a827a761bf326d07c93da34a92a8ae64563d9ece17b94c592ab5b33079b920",
      "scenario/blender/operators.py": "6245f4125a49c3a8d6c461cbf8caee0bf713057b9d3835fb8cab496da6364be3",
      "scenario/blender/panels.py": "aad54275f97ce8645f79863bd0ef55a8a964ca7ceaeecf25fa1f97532a948338",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "d12422eac4229e10bdc5d722890fd56cd998f4c4deec2211d7bf2a3506a80c7f",
      "scenario/blender/composer/modal.py": "c907602659c6921205b9f06989e8c3ca5fc9168d0d1053d83181e008d240cd46",
      "tests/blender/test_composer.py": "8c2a944a24091247b17cfb6f72f96353980ab5584563cac96ceea0c1c79f8f73"
    }
  }
}
---

# Shared Edit 3D form lane rule

Evidence for the [canonical guide](../../architecture/runtime.md).
