---
{
  "type": "Evidence",
  "id": "docs-known-limitations.saved-media-playback",
  "title": "Saved media playback and waveform limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4fbb69e1206ded60ada104df41a0d7c7617dad4b",
    "limits": "Reviewed the saved media bullets against the controller, copy primitive and scheduler: the absent desktop, listening and MCP evidence, lane occupancy by copies and decodes, the four-copy and 1 GiB budget plus player-read copies, the system player tracked only until its launcher exits, whose open copy eviction, retirement or unregistering can then remove, Windows deletion deferred to the day-old sweep, the 60-second decode timeout and 120-second admission expiry, the once-per-second connection check while a waveform is shown and the missing-executable failures. The child start-up figures are carried from the offline envelope review; no new measurement was made. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system player launcher and the animation player process patched. Default-player absence, sandboxed packages and the animation player's soundtrack are stated as unverified. Re-reviewed on 2026-10-12: the evidence sentence now matches the private report of three partial physical passes on macOS arm64 Blender 5.1.2. In the first two, at UI scale 1.0 on ZIPs that predate the measured status wrapping, a saved video opened in the system player and in Blender's animation player and a waveform drew. The third, on a ZIP that had the measured wrapping but predates its Studio popup width declaration and hyphen rule, drew the sidebar rows at UI scales 1.0 and 2.0 (a 1122 px sidebar at 2.0): Waveform reached its summary and icon at both scales and kept 1.00 s whole. result_media.py is unchanged since that ZIP, label_wrap.py changed only for popups (a declared width, and a popup region that is not sized yet) and text_wrap.py only for hyphenated words, which these sidebar texts lack. Play audio, the waveform's desktop Cancel, Retry and close, clicking Play at UI scale 2.0, Studio at UI scale 2.0, other platforms and human listening are stated as without desktop evidence. The draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the summary's no-break spaces were re-checked; these bullets do not describe them. Re-reviewed on 2026-10-12 for the credential-free launch: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment. The bullet now states that both players start without SCENARIO_, PYTHON or proxy variables, how that is tested and that the macOS desktop passes predate this launcher. Unit tests record the launch arguments and filtered environment per platform and refuse relative paths, and a stand-in POSIX xdg-open records the environment a real child process received; installed-ZIP native tests record the saved-result launcher, its pinned copy and a failed launch, and the retained prototype Play and Play in Blender operators. No real default player was started on any platform, and the Windows interpreter helper was not run on Windows. Behavior without xdg-open is handled as a failed launch in code and stays unverified on a desktop. Since the earlier review main changed results.py only for original downloads, OpenEXR originals and splat preparation, not the playback copy.",
    "sources": {
      "scenario/blender/result_media.py": "a7bae9b893ccaffc117f9c4b5dfbd5d9f337d867239e8caf8a4d290eb8fbc429",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "tests/blender/test_result_media.py": "1691143a5c0673fd811651255980faa939a425fbd0837b8eaffc4c86229b6bdd",
      "tests/unit/test_playback.py": "09c7c327ec0adfd7ef0dc711797eaa6430234cf05784fbd2a4f897231af894ba"
    }
  }
}
---

# Saved media playback and waveform limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
