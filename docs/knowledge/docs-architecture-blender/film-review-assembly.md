---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.film-review-assembly",
  "title": "Receipt-bound native Film sequence assembly",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "film-review-assembly",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected native final/previs sequence construction, scope/receipt/measurement checks, independent file copies, exact trims, native audio, editorial loop/duck segments, muted master comparison and rollback. Installed synthetic media tests cover decoder checks and scene library round-trip. Synchronous primitive only: current task/job approval, worker preparation, active UI/MCP controls, mixed-rate normalization, portable export, human audio/motion and release acceptance remain pending. Matching movie/cut rates required; metadata alone is not constant-frame-rate or human quality proof. Preserve media after incomplete rollback. Only this assembly topic was reviewed.",
    "sources": {
      "scenario/blender/film_review.py": "2e3ec05ac4a40506c364a33801a5e2638a5ea46b6602cf2ee69b4927a6a86451",
      "scenario/core/jobs/media_probe.py": "0444d851fa289856cc350e467f929e9c5490d966f56b420055d5e6ad1a0389f1",
      "scenario/core/scene/film_finish.py": "e51114ea696e4eaf3ec61534d0637e76f6ba5335ad8b46102439b79236391a43",
      "scenario/core/scene/film_plan.py": "fea102d507d3544c5ccfa1b89a04743339f88ecbfd65e5aa84384399ae5efa95",
      "tests/blender/test_film_review.py": "5675b01d6da7f1da9455d57e0f4a1375ae7fde5cd4372006cd6c0ff0cd29413b",
      "tests/fixtures/README.md": "cdd7b7d630656b1c03c4831b6cd3ef3f988a3e61a834117db4380c0b7265ebe4",
      "tests/fixtures/synthetic/film-four-seconds.mp4": "b8e01e7a7db99e0dc11311e7119c873046a2772e79b287a32c988acd3516b075",
      "tests/fixtures/synthetic/film-four-seconds-audio.mp4": "16ba84993aae49e22b64c95efe98ceed2ce21f493162953cd0121d7681dc1abb"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/blender.md).
