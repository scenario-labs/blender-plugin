---
{
  "type": "Evidence",
  "id": "docs-ui-style.trained-models-section",
  "title": "Trained models section, strengths and project defaults",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "trained-models-section",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Trained models box that trained_section.draw adds after the Model box in model_picker.draw_model_row, which the sidebar lanes, Studio's Create page and Render Image share: shown for Image and Render Image and elsewhere only while a form holds a choice; one row per LoRA with its name and remove button and a Strength (min to max) field labelled from the current base's declared range (trained_models.base_strength) and clamped by the ScenarioTrainedSlot update, which reprices; slots kept in form order so trained_routes.apply writes aligned loras and lorasScale and a removal shifts no other strength; trained_models.sync_bounds, called from generation.on_model_changed, taking a refreshed range while keeping an out-of-range strength so the request refuses it with the range; Set strength (trained_models.set_strength) as the only way to give a LoRA without a strength the base's visible start value; a base declaring only a default showing and sending it; composition concepts listed read-only; trained_models.selection_error drawn with ERROR, or TIME while loading; Add opening scenario.pick_model on the trained category. Reviewed the project-default row from trained_defaults.view (cached state only) with Use, Save and Clear, Save and Clear carrying the drawn context_id and revision, invoke_confirm before replacing or clearing, and saving or clearing changing no payload or price; forms with no model_key and no trained slot taking the lane default through trained_defaults.apply_pending in the pump and in render_commands.request and inspect, build_request blocked by trained_defaults.blocking_reason with the Applying or unavailable text until then and never priced as the base model alone, repricing whenever that reason changes or ends; an unreadable stored row reported per lane and preserved. Reviewed the composer chip (panels.model_chip_parts and composer_layout.fit_model_label shortening the LoRA name before the count), panels.model_chip_category opening the Trained chip, composer draw.status_note hinting at strength editing when nothing else is shown, and generation.request_meta naming the trained choice for job views of the submitting session. Installed tests compare lane state before and after drawing. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,249 tests (OK, 2 Windows-only skips) with ZIP sha256 269ada4c3673990da2c8735dd8b15f8341c0ad69ed5ef0dc8559d77882a6d8c7, whose 148 Python files match git archive of the reviewed feature commit, including the 16 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). Unit tests cover the label fitting and selection label. Applying a default to a form without an explicit choice follows the proposal made while planning #97 and awaits maintainer confirmation; local MCP has no default tool yet. Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "scenario/blender/trained_section.py": "e4498d61dc304586bcfb4f6b8e487fecb9b18572fcc08587f38560637a4615b5",
      "scenario/blender/trained_defaults.py": "de64246c52dc3107a6892ac9ed0e2a892b4d2a4bcbbd0d3f831f23ec09636648",
      "scenario/blender/trained_models.py": "2c4dadd4a0a5ef2216ca00045b43724da50b5fe5bd1c0bcaddf1a471a3642bd9",
      "scenario/blender/model_picker.py": "3f4bd5d9bd397c8ceb53a62852f1ba458a06ca3bba1f125a66e4163a74b93ff5",
      "scenario/blender/panels.py": "0648fc9699a9a3b2c225acfb25da9ee47c4677d286f9b2c7661789b8a557c7a4",
      "scenario/blender/props.py": "0129dcf9c9a45520f2c0b8b24fa498c49e2244e2417e3d8e8a4866d2ec3ebdbc",
      "scenario/blender/generation.py": "38115244a8350c53148761f57ba0e12ea40ebba64db7e9879f1767dcf444d934",
      "scenario/blender/pump.py": "0839e0c312499ae6292db8aaafe7a9a6ebe5fb3d5e3a81c0f773965fa256b96a",
      "scenario/blender/render_commands.py": "9551e08bb7a898fc9b0872c98a0a5e699ed9c50bede5e8a6e0c69f8cf273f4de",
      "scenario/blender/composer/draw.py": "7041734def6ef04c21d281b77a739efeea38986e48881c7d4ce0b294c2484b42",
      "scenario/blender/composer/modal.py": "ed1863e0d07d941aca94fdbdb89b1e9380760ccab33f4491731827bdad4afc6a",
      "scenario/core/ui/composer_layout.py": "9cfd20a78ad352693a46e58a68eab8b3491e3eda3fc97ebd5d48dd3200c457ae",
      "scenario/core/api/trained_offers.py": "32868cd3552aa856d917e53afa48a5f679de757d9bfe2b15db15a5778665022c",
      "scenario/core/api/trained_routes.py": "908b49b8b5ecdd8ee5869fe07178b80b9e2d3a385b11d694babaf2515a3f0162",
      "tests/blender/test_trained_section.py": "06de61b3c34d0281161432c8f9b637ada8838c760a3b72d977ff9cfe17e18cbf",
      "tests/blender/test_trained_models.py": "405c8e7b43ba0228ede4f6d31fbc2d89c93cdb031b33622dd492e5c689382a14",
      "tests/unit/test_composer_model_label.py": "9a46bf54d2d6baea76361d5331c7aea197a6163c18a292048b9b7d3860068fbc",
      "tests/unit/test_trained_offers.py": "9b715d7f47ffff8ce9e32fc4b15a8a991b88547feda54ce9ca1c6c6f3c4cce83"
    }
  }
}
---

Evidence for [the Trained models section and project defaults](../../UI_STYLE.md#trained-models-section-and-project-defaults).
