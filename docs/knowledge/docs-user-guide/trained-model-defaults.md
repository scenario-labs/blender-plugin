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
    "limits": "Reviewed the user steps against the code: the Trained models box in the sidebar, Studio and Render Image; one Strength field per LoRA limited to the base's declared range; composition LoRAs shown read-only; remove and Add LoRA or composition; Set strength for a LoRA without one and no strength added unseen; the composer chip label opening the Trained chip and strengths edited in the sidebar or Studio; Jobs naming generations submitted in the session; and the project default row: Save only for a choice that runs, a confirmation before replacing, no price requested, Use for a form holding another choice, Clear after a confirmation, a form without a chosen model taking the default once models load, an unavailable default blocking the price with its reason without a base-only fallback, and defaults isolated by credentials and Project ID. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,249 tests (OK, 2 Windows-only skips) with ZIP sha256 269ada4c3673990da2c8735dd8b15f8341c0ad69ed5ef0dc8559d77882a6d8c7, whose 148 Python files match git archive of the reviewed feature commit, including the 16 tests of tests/blender/test_trained_section.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records). Not established: Blender 5.0 and 5.2, Linux and Windows runs; physical desktop interaction (dragging and typing in strength fields, the Save and Clear confirmations, focus, the composer chip at other UI scales, screenshots); live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "scenario/blender/trained_section.py": "e4498d61dc304586bcfb4f6b8e487fecb9b18572fcc08587f38560637a4615b5",
      "scenario/blender/trained_defaults.py": "de64246c52dc3107a6892ac9ed0e2a892b4d2a4bcbbd0d3f831f23ec09636648",
      "scenario/blender/trained_models.py": "2c4dadd4a0a5ef2216ca00045b43724da50b5fe5bd1c0bcaddf1a471a3642bd9",
      "scenario/blender/panels.py": "0648fc9699a9a3b2c225acfb25da9ee47c4677d286f9b2c7661789b8a557c7a4",
      "scenario/blender/props.py": "0129dcf9c9a45520f2c0b8b24fa498c49e2244e2417e3d8e8a4866d2ec3ebdbc",
      "scenario/blender/generation.py": "38115244a8350c53148761f57ba0e12ea40ebba64db7e9879f1767dcf444d934",
      "scenario/blender/pump.py": "0839e0c312499ae6292db8aaafe7a9a6ebe5fb3d5e3a81c0f773965fa256b96a",
      "scenario/blender/composer/draw.py": "7041734def6ef04c21d281b77a739efeea38986e48881c7d4ce0b294c2484b42",
      "scenario/blender/composer/modal.py": "ed1863e0d07d941aca94fdbdb89b1e9380760ccab33f4491731827bdad4afc6a",
      "tests/blender/test_trained_section.py": "06de61b3c34d0281161432c8f9b637ada8838c760a3b72d977ff9cfe17e18cbf"
    }
  }
}
---

Evidence for [project defaults for LoRAs](../../USER_GUIDE.md#project-defaults-for-loras).
