---
{
  "type": "Evidence",
  "id": "docs-film-plan.installed-media-tools",
  "title": "Shared installed ffmpeg and ffprobe lookup",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "installed-media-tools",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "dad196a85368f0adce8fb599b4a613a60a1240df",
    "limits": "Inspected scenario/core/jobs/installed_tools.py and its four callers: media_probe.probe_tool (Film composition and review media inspection), local_render.media_tools (MP4 capture admission in local_capture and rendering), local_export verification and film_export.verifier (the Render video dialog's verification name). Lookup is shutil.which over the current PATH with empty and relative entries removed, rejecting a relative result such as Windows' working directory, then /opt/homebrew/bin, /usr/local/bin and /opt/local/bin on macOS or /usr/local/bin and /usr/bin on Linux; Windows uses PATH only. Only executable regular files count and the result is resolved to an absolute path. It never changes os.environ or runs a program. No preference or environment override for a tool path existed, and none was added. Covers only the sentences that name the shared lookup: local capture's tool check, media_probe's ffprobe requirement, export decode verification and the Render video confirmation's verification name; their neighboring capture, inspection and export claims belong to their own topics. Unit tests in tests/unit/test_installed_tools.py cover PATH precedence, a standard-folder hit with the Dock PATH, a Homebrew-style symlink resolved to its absolute target, ignored non-executable files and folders, ignored working-directory, empty and relative PATH entries, an unset PATH, bare-name validation, PATH-only Windows behavior with a simulated platform, the missing-tool text, an unchanged environment, no process launch, and the probe_tool and media_tools callers; the two caller tests failed against the previous callers. An installed test checks that the export dialog's verifier finds a fake standard-folder ffprobe with the Dock PATH and reports Blender's check without it. A reproduction with the Dock PATH on macOS arm64 and Homebrew ffmpeg failed before the change and resolved the Homebrew binaries after it. The packaged ZIP passed 1,862 installed tests (3 Windows-only skips) on Blender 5.1.2 macOS arm64 only. Linux and Windows lookups rely on unit tests with simulated folders and platform; no Dock- or Finder-launched desktop Blender session, Linux desktop launch or Windows run was performed for this change, and /snap/bin is excluded by design rather than tested against a snap install.",
    "sources": {
      "scenario/core/jobs/installed_tools.py": "e1836a8efd1a7625e4fed719fb39863c40fd609432a87fba95d831df98c0f987",
      "scenario/core/jobs/media_probe.py": "a5a1d357cb51809060c5275f9ddcc2eae7f161c1d8e7ee4cacedd259de80a0e4",
      "scenario/core/jobs/local_render.py": "24524eb2d2cbfb148b09bc427ae481d0945586fc9e41799a62a251e6a38bac70",
      "scenario/core/jobs/local_export.py": "24337770c351cdb2de440bb1bea1c7fc1c9e1c5614987dd056fb96cbff4c433e",
      "scenario/blender/film_export.py": "9e1bd807eee291de319408f442effa673c33ba0dcb401c07592c91ce60f3fbff",
      "scenario/blender/local_capture.py": "d1d3a5bde72ca1f61bf879fbc971bbca59d344e31a6a5c96e42558148537a43d",
      "tests/unit/test_installed_tools.py": "73d76a0838acd3f70b0298e307071e5b7b16c390b52e918bf4da252810590bf1",
      "tests/unit/test_media_probe.py": "986cc6a118eae2b8f060609497de731140580c1ebe3903ed08fab69bcd054ebd",
      "tests/unit/test_local_render.py": "42c227a9c90412b72968d7621bba4b36195360570cfe6bca3a0eb97d3d80c2ea",
      "tests/unit/test_local_export.py": "741bc8623f1d26a7b19a5639500d0fb3649889de7a066101d39f4b46f8f332c8",
      "tests/blender/test_film_export_controls.py": "6c3c23e256a9075ba86153e80d9e4b13ab647ae2df6cab7aada306d566022665",
      "tests/blender/test_film_export_primitive.py": "88394b5c3c9ad6e2d4b4466197b6a39d71db3a1526bdb9de91042f8dcdad8a90"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
