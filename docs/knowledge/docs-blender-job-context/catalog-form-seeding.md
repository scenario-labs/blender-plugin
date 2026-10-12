---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.catalog-form-seeding",
  "title": "Catalog loads keep captured origins",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "catalog-form-seeding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed dependency-update origin invalidation against catalog form synchronization and automatically applied trained-model project defaults only. Catalog seeding and model-index restoration avoid RNA update callbacks, so a catalog load no longer makes origins, quotes or approvals captured before it stale; explicit selections and edits that assign a property with an RNA update callback still invalidate them. Re-reviewed on 2026-10-12 for the sentence on project defaults: trained_defaults.apply_pending, which the GUI pump, local MCP render inspection and quotes, Save and Clear call, applies a default to a form without an explicit choice through _apply with seed, which stores the model enum index and each LoRA strength (trained_models.write_slots) as raw ID properties, runs generation.on_model_changed itself and re-arms the form's price; Use (trained_defaults.use) still assigns through RNA; re-reviewed again on 2026-10-12: of what it writes, only a different base model and each LoRA strength with a declared range have an update callback (props: model_id and ScenarioTrainedSlot.scale), so a composition used on the form's current base writes only model_key, plain slot fields and the trained collection, leaving origins current while props.mark_estimate_dirty re-arms the form's price. The trained catalog events write only slot kinds, names and strength bounds, which have no update callback. JobSession._scene_changed, invalidate_scene and capture are unchanged by main's later job_session.py changes (preview, export and Film review ownership). Installed Blender 5.1.2 regressions cover a session origin across the first load and a restored model index, an MCP approval across a seeding catalog load, and origins captured in two scenes staying current while apply_pending applies a default there, with a Use assigning a different base invalidating one (test_trained_section.test_an_automatic_default_keeps_origins_captured_before_it, which failed before the raw writes), and, on the form's current base, a stack's Use invalidating through its strengths while a composition's Use leaves the origin current (test_use_on_the_current_base_stales_origins_only_through_strengths). Re-checked on 2026-10-12 for the local MCP trained-model additions: generation.ensure_record's WithoutInputs, params_ui.collect_values' float32_decimal spelling, trained_defaults.store, explicit_default and lane_summary, and trained_models' listed_reason, split_parameters, apply_picks, checked_choice and payload_meta write no form property; local MCP model_defaults set reaches forms only through trained_defaults.store and apply_pending; render_commands.configure's trained setting (trained_models.replace_choice) is an explicit choice whose writes go through RNA only for LoRA strengths with a declared range (trained_models.write_slots), so trained: [] or a composition on the shown model, with no other setting, writes only model_key and the trained list and re-arms the form's price. Other origin, render-thread, deletion and history claims retain prior evidence. No desktop timing, other Blender series, live or release acceptance is established. Re-checked on 2026-10-12 after the replay onto the picker branch's repricing fix (c05d1fea): params_ui.sync_params now also calls props.mark_estimate_dirty when it drops a value of the form's own model. That writes only the estimate state, which has no update callback, so catalog synchronization still leaves captured origins current; only the params_ui.py fingerprint is refreshed.",
    "sources": {
      "scenario/blender/job_session.py": "283300899c616cbb4a2ae9f81751e2ab189c1f5b10c8acaf51da07be56cb6c29",
      "scenario/core/jobs/origins.py": "d1282d67aacdfe2444a776cf1338667bea9ee67392ff3f473db581a0f8059977",
      "scenario/blender/generation.py": "23fb25c256b3896a3cc0fa61c02b8821476c739d5559499f1ae485579c47d385",
      "scenario/blender/params_ui.py": "bc4c54873c5fcada0ce7754af7d40cd8ac33a34b0c76cadda68c583b736b5af4",
      "tests/blender/test_generation.py": "27b397a4c8487f84150cdcd065f407c0fd671e7a01a994c0af04338f82fbc5d4",
      "tests/blender/test_model_generation.py": "8664c2f3cd296fc005a77d3d4009865df3e8b5bfdda3a6bbc9a2ed762bb32b68",
      "scenario/blender/trained_defaults.py": "e38474e5174121bf5b6771a6e134ebd5744d7a6d7e717eb7473098c37ad5cf0e",
      "scenario/blender/trained_models.py": "5dd2c49632443a65f0db877732f7179172e259db5f96fbe6051a4129833eeb52",
      "tests/blender/test_trained_section.py": "c0e2338e7c172c836d67d97ef9f1beee471e77e4be9824e9659631c245ab6eeb",
      "scenario/blender/props.py": "1d43b48ce3c6a268cc478077f107c9b3625efd61d14cd624f208cba58fc28051",
      "scenario/blender/render_commands.py": "b81110ef301496c0110d813f1d47af34326eebd71b87d399a3b5a7767ec2685e"
    }
  }
}
---

Evidence for the [canonical guide](../../BLENDER_JOB_CONTEXT.md).
