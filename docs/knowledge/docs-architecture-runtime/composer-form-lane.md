---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.composer-form-lane",
  "title": "Shared Edit 3D form lane rule",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the shared lane rule and its callers: the pricing pump's visible lane, the sidebar and Settings form choice, the composer state, draw and modal handler and the Generate operator, plus the model picker's model-to-form mapping and the composer's commit guard, including its lane tab and double-click paths. Lane-bound quote validation and durable submission in generation.py and model_jobs.py are unchanged. Installed offline tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the Edit quote being consumed by the composer while a ready 3D-tab quote is left untouched, no request when only the 3D-tab price is ready, and no write or request after the form behind a focused prompt changed, including after a lane tab or a double-click. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's prepared job cancellation, experimental status, Codex token, handbook, sidebar status wrapping, World panorama, trained model catalog and job strip changes: the model picker only gains a read-only experimental status label and the sidebar only wraps its status labels, so the lane rule, the Generate row choice and the model-to-form mapping are unchanged. Rechecked after rebasing onto main's overlapping-sidebar composer, saved-job action descriptors, history kind, captured origin, selected-scene pricing and cancellable inference changes: the pump now prices only the selected scene, still for its visible lane, the model chip opens the sidebar only when the card fits beside it, Settings goes through one helper that still opens the tab's form, and a card that gives way to the pill ends a focused prompt without writing a replaced form, so the lane rule, its callers, the commit guard and the model-to-form mapping are unchanged. Rechecked after rebasing onto main's composer double-click pairing and whole-viewport clamp, World candidates and history paging, workflow step decisions, trained model routes and defaults, saved result previews, workflow input uploads, original result assets and upload staging cleanup: a paired press reaches the double-click branch, which still keeps the commit guard for a replaced form and a field without a prompt, the second press of a double-click on Generate submits nothing more, and the sidebar only changes its history rows, so the lane rule, its callers, the commit guard and the model-to-form mapping are unchanged. The rebased ZIP was rerun only on macOS arm64 Blender 5.1.2, where every composer test passes. No live provider pricing, physical desktop input or release acceptance is claimed. Rechecked after the composer session lifetime change: modal.py only gains a wrapper that ends the session when modal raises and a cancel callback, both of which leave a focused prompt, and test_composer.py only gains lifetime and file-load tests, so the lane rule, its callers, the commit guard and the Generate dispatch are unchanged; every installed composer test passes on macOS arm64 Blender 5.1.2. Rechecked after rebasing onto main's input-method text field: its modal changes move the replaced-form and no-prompt text guard into refuse_text, which named text keys, untyped keys with text, F2, a composition's second press and the text field's confirmation share, with the same order and messages, and the new paths type only through that guard and the lane commit; this change's tests only gain session-end tests, so the lane rule, its callers, the commit guard and the Generate dispatch are unchanged. The full installed suite (1,448 tests) passes on macOS arm64 Blender 5.1.2. Rechecked after the resize cursor fix: modal.py only changes _finish to also restore the window's cursor when the session ends with the pointer resting on the resize corner, and test_composer.py only gains that cursor test, so the lane rule, its callers, the commit guard and the Generate dispatch are unchanged. The full installed suite (1,449 tests) passes on macOS arm64 Blender 5.1.2. A scoped re-inspection for the compact composer job strip found that composer/state.py only gains the job strip's Python display caches, shown_actions and shown_form, which returns the (tab, lane) the draw computed inline before; the lane rule, prompt mirror and commit guards are unchanged. The review date and earlier evidence are unchanged.",
    "sources": {
      "scenario/blender/props.py": "ae85f36f0e051e578466776ffff2c74f8ba70dc8b06506030aff81b6d80f3d40",
      "scenario/blender/operators.py": "6245f4125a49c3a8d6c461cbf8caee0bf713057b9d3835fb8cab496da6364be3",
      "scenario/blender/panels.py": "6ebb4781ff62c6a155bc1db067a40eb33f6107cd34325d040fac3c877d0cbde6",
      "scenario/blender/pump.py": "14ca29af007afa5dbf35c7f39a3caf39a709914a16f8cefa938dff58efcf7f2d",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/composer/state.py": "a71bbd1a1497c199a6835387dac27249b339b9a6397b992be56cf3cddaa35b66",
      "scenario/blender/composer/draw.py": "4806dd6d6972920493ed90adf98aba673814abf525affad7bd4234579180a8a9",
      "scenario/blender/composer/modal.py": "40df6decea7237f2d1afe85e4b6bad62dcc03667584284267e48b3cd582d2fde",
      "tests/blender/test_composer.py": "c2df49957903582c4405ffe7702aa12ee050d414f1cf6ce7a2c2bbaf88c9d0ae"
    }
  }
}
---

# Shared Edit 3D form lane rule

Evidence for the [canonical guide](../../architecture/runtime.md).
