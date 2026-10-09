---
{
  "type": "Evidence",
  "id": "docs-known-limitations.splat-decoding",
  "title": "Saved splat decoding limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "splat-decoding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Checked the limitation against the decoder version checks, compressed splat PLY rejection, the SPZ extension flag that is kept while extension records are not read, the absence of saved-job splat import controls and the prototype point-cloud presentation. No native desktop review, provider file or live acceptance; this topic covers only the splat bullet.",
    "sources": {
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/scene/spz.py": "b2ad27549bd7c08f76b0987844071e8538afb3259d918e9a9d77157f8737b72c",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "scenario/blender/apply_splat.py": "a1cfdbfdfabdb27c6ed736702c301f3928edad8a8736de3774f4229732117d80",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c"
    }
  }
}
---

# Saved splat decoding limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
