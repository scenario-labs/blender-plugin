---
{
  "type": "Evidence",
  "id": "docs-known-limitations.splat-decoding",
  "title": "Saved splat decoding limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "splat-decoding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Checked the limitation against the decoder version checks, compressed splat PLY rejection, the SPZ extension flag that is kept while extension records are not read, the absence of saved-job splat import controls (saved-job controls cover GLB models, images, World panoramas and audio or video media only) and the prototype point-cloud presentation. No native desktop review, provider file or live acceptance; this topic covers only the splat bullet.",
    "sources": {
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/scene/spz.py": "dab0ca7fd16ca7dd9366d1c52e64513dd06bb78d1b82bd3dbe887ce9e59bff0a",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "scenario/blender/apply_splat.py": "a1cfdbfdfabdb27c6ed736702c301f3928edad8a8736de3774f4229732117d80",
      "scenario/blender/model_jobs.py": "553e74a31bfdef53e93216e48b650d23d8c6bf2da99a1431e63d4722c956d49c"
    }
  }
}
---

# Saved splat decoding limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
