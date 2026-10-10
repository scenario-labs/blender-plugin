---
{
  "type": "Evidence",
  "id": "docs-user-guide.trained-model-defaults",
  "title": "Strengths and project defaults for trained models",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "trained-model-defaults",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the user steps against the code: the Trained models box in the sidebar, Studio and Render Image; one Strength field per LoRA limited to the base's declared range; composition LoRAs shown read-only; remove and Add LoRA or composition; Set strength for a LoRA without one and no strength added unseen; the composer chip label opening the Trained chip and strengths edited in the sidebar or Studio; Jobs naming generations submitted in the session; and the project default row: Save only for a choice that runs, a confirmation before replacing, no price requested, Use for a form holding another choice, Clear after a confirmation, a form without a chosen model taking the default once models load, an unavailable default blocking the price with its reason without a base-only fallback, and defaults isolated by credentials and Project ID. Re-reviewed with the fix commit: Save requests no price for the saving form even when another scene's form takes the default (props._find_lane_state), a default lands only on a base the form lists, and the steps above are unchanged. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,254 tests (OK, 2 Windows-only skips) with ZIP sha256 5d94b5a727a8b20cf3640b15b1c4446053d79a75905fc79b1f282a84b119298c, whose 148 Python files match git archive of the reviewed fix commit, including the 21 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "scenario/blender/trained_section.py": "e4498d61dc304586bcfb4f6b8e487fecb9b18572fcc08587f38560637a4615b5",
      "scenario/blender/trained_defaults.py": "ccf522bd4326d15d86885bdedeee7fbb44b82b8c086ca9c206c8d9e8356932a6",
      "scenario/blender/trained_models.py": "2c4dadd4a0a5ef2216ca00045b43724da50b5fe5bd1c0bcaddf1a471a3642bd9",
      "scenario/blender/panels.py": "0648fc9699a9a3b2c225acfb25da9ee47c4677d286f9b2c7661789b8a557c7a4",
      "scenario/blender/props.py": "49b6976e43affda255eff6622f3e397d344f001b061e090803d4f6b7f7110746",
      "scenario/blender/generation.py": "339ce612dd6d2dc0fe05478d53f1742ed267f3363465ce4cac68ea4b011c1920",
      "scenario/blender/pump.py": "0839e0c312499ae6292db8aaafe7a9a6ebe5fb3d5e3a81c0f773965fa256b96a",
      "scenario/blender/composer/draw.py": "7041734def6ef04c21d281b77a739efeea38986e48881c7d4ce0b294c2484b42",
      "scenario/blender/composer/modal.py": "ed1863e0d07d941aca94fdbdb89b1e9380760ccab33f4491731827bdad4afc6a",
      "tests/blender/test_trained_section.py": "cccd18467914ad3e62f00a7e7c302b08b34ceac96f7ded93be59d47c85d9800a"
    }
  }
}
---

Evidence for [project defaults for LoRAs](../../USER_GUIDE.md#project-defaults-for-loras).
