---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.catalog-form-seeding",
  "title": "Catalog form seeding without scene updates",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "catalog-form-seeding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Catalog, model-detail and model-restore form synchronization stores schema defaults, enum corrections and restored model enum indices as raw ID properties, so it runs no RNA update callback and does not tag the scene for a dependency update. A seeded form re-arms its own price in its own scene and a seeded duration still drives the camera path. Native Blender 5.1.2 probes showed that any RNA assignment to a property with an update callback tags the Scene even with an unchanged value, while plain properties, collection add/remove and raw ID property writes do not. Installed regressions cover the first load, a restored enum index, per-scene repricing, seeded duration, explicit edits that still invalidate, and an MCP approval surviving a seeding catalog load. A temporary pre/post dump of every lane field, estimate state and shot duration was identical for first load, explicit selection and reload. The Edit 3D default selection when a saved index falls outside the task list still uses RNA and stays conservative. Re-reviewed on 2026-10-12 for the trained-model additions and the sentence on project defaults: sync_params also hides a base's LoRA inputs, and trained_models.adopt_typed turns a saved text-field ID into a slot without any field that has an update callback; the trained catalog events write only slot kinds and names before re-arming prices, and deliver base descriptions through set_models without dirty intent; trained_models.sync_bounds writes only strength bounds; trained_defaults.apply_pending stores a default's model enum index and strengths raw (_apply with seed, trained_models.write_slots), runs on_model_changed itself and re-arms the form's price. Re-reviewed again on 2026-10-12 for the narrowed sentence on explicit changes: Use (_apply without seed), like the picker's trained_models.choose, assigns through RNA only a different base model (model_id, whose update runs on_model_changed) and each LoRA strength with a declared range (ScenarioTrainedSlot.scale, the slot's only property with an update callback); model_key, the other slot fields and the trained collection have none, so a composition used on the form's current base leaves origins captured in its scene current while props.mark_estimate_dirty re-arms the form's price and clears its estimate key; render_commands.configure assigns model_id through RNA only when it changes the model. Installed regressions (test_trained_section) keep origins captured in two scenes current across apply_pending, show that a Use assigning a different base invalidates one, and show that on the form's current base a stack's Use invalidates through its strengths while a composition's Use leaves the origin current, both repricing the form. No desktop timing, other OS or Blender series, live catalog or release acceptance is established. Re-checked on 2026-10-12 after the replay onto the picker branch's repricing fix (c05d1fea): params_ui.sync_params now also calls props.mark_estimate_dirty when it drops a value of the form's own model. That writes only the estimate state, which has no update callback, so catalog synchronization still leaves captured origins current; only the params_ui.py fingerprint is refreshed.",
    "sources": {
      "scenario/blender/generation.py": "d00e21459c5a0c9a8757e5ed53fc829c3a5d7002797d50e7d69b6d0db712d566",
      "scenario/blender/params_ui.py": "c41d76277605de313226da7696b700617c67f2c63b013af552cc4fd1d0feb78b",
      "scenario/blender/props.py": "1d43b48ce3c6a268cc478077f107c9b3625efd61d14cd624f208cba58fc28051",
      "scenario/blender/render_commands.py": "87864f3b6a908a068daabe2aac0bc5882c12f861bb84ff60b32101a029aff319",
      "scenario/blender/handlers.py": "0dccbbd97f2be476960f2709516989e6f218bd7372ef003c15138ddf6c737eb7",
      "tests/blender/test_generation.py": "27b397a4c8487f84150cdcd065f407c0fd671e7a01a994c0af04338f82fbc5d4",
      "tests/blender/test_model_generation.py": "8664c2f3cd296fc005a77d3d4009865df3e8b5bfdda3a6bbc9a2ed762bb32b68",
      "scenario/blender/trained_defaults.py": "df72a33f70df469e124a16a65221a4a919e145ff24529cd3eaaa864a5e771ed8",
      "scenario/blender/trained_models.py": "36f16dd75a5cf822bae5be7387c48aad1daa15ed837d2244255661a8f44545f7",
      "tests/blender/test_trained_section.py": "c0e2338e7c172c836d67d97ef9f1beee471e77e4be9824e9659631c245ab6eeb"
    }
  }
}
---

Evidence for the [canonical guide](../../architecture/runtime.md).
