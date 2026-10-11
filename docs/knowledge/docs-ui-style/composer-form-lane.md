---
{
  "type": "Evidence",
  "id": "docs-ui-style.composer-form-lane",
  "title": "Composer form lane in 3D Edit mode",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Source-reviewed the composer tab, prompt mirror and commit guard, model chip, price label, status line, enablement, Generate/Enter/Esc/collapse/drag dispatch, the lane tab and double-click focus rules, the Settings and model chip flush, the no-prompt placeholder and text-key guard, the sidebar and Settings Edit form, the Generate operator and the model picker's model-to-form mapping. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's prepared job cancellation, experimental status, Codex token, handbook, sidebar status wrapping, World panorama, trained model catalog and job strip changes: the model picker only gains a read-only experimental status label, the sidebar only wraps its status labels, the layout module only gains job strip geometry after the composer layout, and the generation fixture only gains tests and a panorama helper option, so the lane rule, the Generate row choice, the composer strings, the model-to-form mapping and the fixture's default dry-run cost are unchanged. Rechecked after rebasing onto main's overlapping-sidebar composer, saved-job action descriptors, history kind, captured origin, selected-scene pricing and cancellable inference changes: the model chip opens the sidebar only when the card still fits beside it, Settings and the no-room pill open the tab's form through one Settings helper, the composer scales with Blender's custom-interface UI scale and keeps clear of side regions, a card that gives way to the pill ends a focused prompt without writing a replaced form (an exit this guide does not list), the pump prices only the selected scene's visible lane, and the sidebar and fixture changes leave the Generate row choice and the fixture's default dry-run cost alone, so the lane rule, the dialog flush, the composer strings and the model-to-form mapping are unchanged; the Edit form draw fixture now supplies Blender's UI scale. Run against the base revision's product code on macOS arm64 Blender 5.1.2, the installed composer tests report 20 failures and 3 errors, all in the Edit form tests: the card showed the Text form's 1.5 CU price and that quote enabled its Generate while the operator routes the 3D tab in Edit mode to the Edit form's 7.25 CU quote, the sidebar Edit Generate stayed disabled for its own quote, the model chip picked for the 3D-tab form, Settings and the model chip opened their dialogs with the prompt still focused, and keys typed after a mode switch still edited the Text prompt. The lane tab, double-click and model-change rules came after the GUI check below: on the composer code that check ran, their 4 installed tests report 5 failures, one in each of 3 tests and one in each of the replaced-form test's 2 tab subtests. Installed tests run the real composer draw function with recording drawing primitives and the real modal handler, operator and offline SDK transport; before that rebase, the packaged ZIP passed 1,221 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. The rebased ZIP f88503cdd1f6d01cdcbebed9d9b2e7e914b2df4e75d3717da42fc4025644859b runs 1,313 installed tests on macOS arm64 Blender 5.1.2 with every composer test passing and one failure elsewhere, a saved-job action label test that main 72723f02a also fails; it was not rerun on 5.0.1 or 5.2.1. A private offline GUI check ran the earlier ZIP 89c07a5b0642ca02b53d5c1fcb57968f03fde32b3ae942ac7f048690f9272011 in an isolated profile on the same three versions through Blender's event queue (--enable-event-simulate, window without focus, no OS input injected), recorded prompts and screenshots after each step, saw no network activity and left the normal profile unchanged; it did not exercise the lane tab, double-click or model-change rules. Offline, no price was ready and the Settings dialog showed its loading state, so the mode switch was a property change while it was open, and Generate could not submit. The blur click's missing viewport selection was observed on an unchanged code path. Physical HID keyboard/pointer input, IME, focus across applications, other OS/DPI, live pricing and paid submission are not established.",
    "sources": {
      "scenario/blender/props.py": "ae85f36f0e051e578466776ffff2c74f8ba70dc8b06506030aff81b6d80f3d40",
      "scenario/blender/operators.py": "6245f4125a49c3a8d6c461cbf8caee0bf713057b9d3835fb8cab496da6364be3",
      "scenario/blender/panels.py": "6f8aa0ae9842509b1d93dc9a3e57a59ab8225b172ac577b5bf10586e12c2fc21",
      "scenario/blender/pump.py": "14ca29af007afa5dbf35c7f39a3caf39a709914a16f8cefa938dff58efcf7f2d",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "4806dd6d6972920493ed90adf98aba673814abf525affad7bd4234579180a8a9",
      "scenario/blender/composer/modal.py": "027be2cf79c1dd8d22df65889319d7eced5251b5e71d425a927fee42ce211593",
      "scenario/core/ui/composer_layout.py": "cca5f608aeb8648ec8ee91de5d38dcbccbd08f280818cfde7bd703afb12da592",
      "tests/blender/test_composer.py": "d8e879cb60eabb28febed0154974b121b54990c73a75d6c8c1606cddc7c47b37",
      "tests/blender/test_model_generation.py": "906afa92d48f94bf5c95e63fa5999db7ef94e59f69452f7fa11069a218fe7f39",
      "tests/unit/test_composer_layout.py": "d1e8bff529c096f88eb96a99d5ab9ad6eb95bdd5d033a0581ef0330f723f83fb"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the [UI style guide](../../UI_STYLE.md#buttons): with the 3D tab in Edit
mode, the composer shows, prices and submits the Edit 3D form, a ready 3D-tab
price never labels or enables that submission, and a focused prompt never writes
into a form that replaced the one it was synchronized from.
