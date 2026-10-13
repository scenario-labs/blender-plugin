---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.source-selection",
  "title": "Selected Studio source revision and intake boundaries",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "source-selection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "Read-only check on 2026-10-13 of the public upstream repository edemaistre/scenario-blender-studio: main and annotated tag v0.2.0 both resolve to commit 204c847ad6f999e1050070a35e58af666b28ff9c, one commit after e2b0277064f0c502d46524fba1d006d0ac83f846, with no later push. Tree IDs for src/scenario_studio, tests and src/scenario_studio/resources were read with git rev-parse; git diff showed resources, the package LICENSE.txt and THIRD_PARTY_NOTICES.md unchanged since 0.1.5, and listed 43 added and 23 modified modules under src/scenario_studio, no removed module. Authorship and the co-author trailer were read from the commit. The intake exclusions were checked against the 0.2.0 tree listing. The canonical baseline statement was checked against .release-please-manifest.json and the build path against tools/build.py and the manifest. No Studio code was imported or executed, and no upstream test, headless check or live result was reproduced. The upstream notes archive shared outside the repository was not part of this review. Adaptations recorded elsewhere in this document keep their 0.1.5 provenance.",
    "sources": {
      ".release-please-manifest.json": "5772543331b712ae865fb3fb2001c7512d49385a02b9743a67116b97a53e5e38",
      "scenario/blender_manifest.toml": "b77719e7bab76f1dcc159c7c281c404e70bf8d5ad9614beb757ebb34aff29110",
      "tools/build.py": "162e00bb52f46770d219c5570d3ceccf3bd98e87055026c5a39944aec39f6bdd"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
