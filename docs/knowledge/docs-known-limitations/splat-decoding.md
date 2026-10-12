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
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Checked the limitation against the decoder version checks, compressed splat PLY rejection, the SPZ extension flag that is kept while extension records are not read, the prototype point-cloud presentation. No native desktop review, provider file or live acceptance; this topic covers only the splat bullet. On 2026-10-10 the bullet was rewritten for saved splat import and apply_splat.py now delegates to the shared builder; the decoding claims above were rechecked and are unchanged, and import, presentation and axis claims are covered by docs-known-limitations.saved-splat-import. The review date is unchanged.",
    "sources": {
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/scene/spz.py": "dab0ca7fd16ca7dd9366d1c52e64513dd06bb78d1b82bd3dbe887ce9e59bff0a",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "scenario/blender/apply_splat.py": "95562972fc2a8f49e10ddac30563d55b434160246b6fa323ba288d4d1338c23e",
      "scenario/blender/model_jobs.py": "24b608edabf19ad9c8176e08ebc3db51ac5ad9acbb960f1bba39368a5f1c5dec"
    }
  }
}
---

# Saved splat decoding limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
