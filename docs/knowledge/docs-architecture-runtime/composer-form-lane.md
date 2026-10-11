---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.composer-form-lane",
  "title": "Shared Edit 3D form lane rule",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the shared lane rule and its callers: the pricing pump's visible lane, the sidebar and Settings form choice, the composer state, draw and modal handler and the Generate operator, plus the model picker's model-to-form mapping and the composer's commit guard, including its lane tab and double-click paths. Lane-bound quote validation and durable submission in generation.py and model_jobs.py are unchanged. Installed offline tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the Edit quote being consumed by the composer while a ready 3D-tab quote is left untouched, no request when only the 3D-tab price is ready, and no write or request after the form behind a focused prompt changed, including after a lane tab or a double-click. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's prepared job cancellation, experimental status, Codex token, handbook, sidebar status wrapping, World panorama, trained model catalog and job strip changes: the model picker only gains a read-only experimental status label and the sidebar only wraps its status labels, so the lane rule, the Generate row choice and the model-to-form mapping are unchanged. Rechecked after rebasing onto main's overlapping-sidebar composer, saved-job action descriptors, history kind, captured origin, selected-scene pricing and cancellable inference changes: the pump now prices only the selected scene, still for its visible lane, the model chip opens the sidebar only when the card fits beside it, Settings goes through one helper that still opens the tab's form, and a card that gives way to the pill ends a focused prompt without writing a replaced form, so the lane rule, its callers, the commit guard and the model-to-form mapping are unchanged. The rebased ZIP was rerun only on macOS arm64 Blender 5.1.2, where every composer test passes. No live provider pricing, physical desktop input or release acceptance is claimed.",
    "sources": {
      "scenario/blender/props.py": "ae85f36f0e051e578466776ffff2c74f8ba70dc8b06506030aff81b6d80f3d40",
      "scenario/blender/operators.py": "6245f4125a49c3a8d6c461cbf8caee0bf713057b9d3835fb8cab496da6364be3",
      "scenario/blender/panels.py": "6f8aa0ae9842509b1d93dc9a3e57a59ab8225b172ac577b5bf10586e12c2fc21",
      "scenario/blender/pump.py": "14ca29af007afa5dbf35c7f39a3caf39a709914a16f8cefa938dff58efcf7f2d",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "4806dd6d6972920493ed90adf98aba673814abf525affad7bd4234579180a8a9",
      "scenario/blender/composer/modal.py": "027be2cf79c1dd8d22df65889319d7eced5251b5e71d425a927fee42ce211593",
      "tests/blender/test_composer.py": "d8e879cb60eabb28febed0154974b121b54990c73a75d6c8c1606cddc7c47b37"
    }
  }
}
---

# Shared Edit 3D form lane rule

Evidence for the [canonical guide](../../architecture/runtime.md).
