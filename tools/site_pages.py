# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the site's downloads pages with the handbook's header, footer and stylesheet.

The pages live in `repo/` beside the handbook. They inline docs/site.css and the
wordmark, so they render without the handbook's copied images.
"""

import base64
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://blender.scenario.com/repo/index.json"
RELEASES_URL = "https://github.com/scenario-labs/blender-plugin/releases"
PLATFORMS = {
    "linux-x64": "Linux x64",
    "windows-x64": "Windows x64",
    "windows-arm64": "Windows Arm64",
    "macos-arm64": "macOS Apple silicon",
    "macos-x64": "macOS Intel",
}
COPY_SCRIPT = """<script>
document.addEventListener("click", async event => {
  const button = event.target.closest("button[data-copy]");
  if (!button) return;
  try {
    await navigator.clipboard.writeText(button.dataset.copy);
    button.textContent = "Copied";
  } catch {
    button.textContent = "Select and copy";
  }
  setTimeout(() => { button.textContent = "Copy"; }, 2000);
});
</script>"""


def _style():
    style = (ROOT / "docs/site.css").read_text(encoding="utf-8")
    if "</style" in style.casefold():
        raise ValueError("site.css must not close its <style> element")
    return style


def _wordmark():
    data = (ROOT / "docs/images/scenario-wordmark.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode("ascii")


def _page(title, body, *, script=""):
    logo = _wordmark()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400..700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap">
<style>{_style()}</style>
</head>
<body>
<a class="skip" href="#main">Skip to downloads</a>
<header class="site-header">
  <div class="bar">
    <a class="brand" href="../">
      <img src="{logo}" alt="Scenario" width="112" height="28">
      <span class="chip product">Blender</span>
    </a>
    <nav class="site-nav" aria-label="Site">
      <a class="optional" href="../#install">Install</a>
      <a href="./" aria-current="page">Downloads</a>
      <a class="optional" href="{RELEASES_URL}">Changelog</a>
      <a class="optional" href="https://github.com/scenario-labs/blender-plugin">GitHub</a>
      <a class="button" href="https://app.scenario.com/">App Login</a>
    </nav>
  </div>
</header>
{body}
<footer class="site-footer">
  <div class="bar">
    <img src="{logo}" alt="Scenario" width="92" height="23">
    <a href="../">Handbook</a>
    <a href="https://github.com/scenario-labs/blender-plugin">Source on GitHub</a>
    <a href="https://github.com/scenario-labs/blender-plugin/blob/main/CHANGELOG.md">Release notes</a>
    <a href="https://github.com/scenario-labs/blender-plugin/blob/main/docs/PRIVACY.md">Privacy</a>
    <span class="legal">GPL-3.0-or-later · Scenario is a trademark of Scenario Inc.</span>
  </div>
</footer>
{script}
</body>
</html>
"""


def _version_key(item):
    return tuple(int(part) for part in re.findall(r"\d+", item["version"])[:3])


def _blender_range(item):
    if "blender_version_max" in item:
        return f"{item['blender_version_min']} to {item['blender_version_max']} (exclusive)"
    return f"{item['blender_version_min']} or newer"


def _release(item, latest):
    escape = html.escape
    digest = item["archive_hash"].removeprefix("sha256:")
    platforms = " · ".join(PLATFORMS.get(name, name) for name in item.get("platforms", ["all"]))
    badge = ' <span class="latest">Latest</span>' if latest else ""
    return f"""<li class="release">
  <h3>{escape(item["name"])} {escape(item["version"])}{badge}</h3>
  <a class="button" href="{escape(item["archive_url"], quote=True)}">Download ZIP</a>
  <dl>
    <dt>Blender</dt><dd>{escape(_blender_range(item))}</dd>
    <dt>Platforms</dt><dd>{escape(platforms)}</dd>
    <dt>Size</dt><dd>{item["archive_size"] / 1_000_000:.1f} MB</dd>
    <dt>SHA-256</dt><dd class="hash"><code>{escape(digest)}</code><button class="button quiet" type="button" data-copy="{escape(digest, quote=True)}">Copy</button></dd>
  </dl>
</li>"""


def downloads_page(index):
    """The listing of a verified repository index, newest release first."""
    items = sorted(index["data"], key=_version_key, reverse=True)
    releases = "\n".join(_release(item, number == 0) for number, item in enumerate(items))
    url = html.escape(REPOSITORY_URL, quote=True)
    body = f"""<main class="downloads" id="main">
<p class="eyebrow">Extension repository</p>
<h1>Scenario for Blender <em>downloads</em></h1>
<p class="lede">Add this repository to Blender to install Scenario and receive its updates, or download a release ZIP and install it from disk.</p>
<section class="panel" aria-labelledby="add-repository">
  <p class="eyebrow" id="add-repository">Add this repository in Blender</p>
  <div class="copy-row"><code>{url}</code><button class="button quiet" type="button" data-copy="{url}">Copy</button></div>
  <p>In Edit › Preferences › Get Extensions › Repositories, choose Add Remote Repository and paste this address. <a href="../#install">Installation steps</a></p>
</section>
<h2>Releases</h2>
<ol class="releases">
{releases}
</ol>
<p class="note">Check a download before installing it: <a href="../#verify-your-download">Verify your download</a>. Blender reads the same files from the <a href="./index.json">repository index</a>.</p>
</main>"""
    return _page("Scenario for Blender: downloads", body, script=COPY_SCRIPT)


def pending_page():
    """The downloads page before the first adopted release is published."""
    body = f"""<main class="downloads" id="main">
<p class="eyebrow">Extension repository</p>
<h1>Native downloads are <em>coming</em></h1>
<p class="lede">The official extension repository will become available after the first verified release. No native update index is published yet.</p>
<section class="panel">
  <p class="eyebrow">Earlier builds</p>
  <p><a href="{RELEASES_URL}">Browse historical ZIP releases</a>. These are earlier experimental builds. Their features, controls and Blender requirements may differ from the current handbook. Follow the requirements and installation instructions attached to the release you choose.</p>
</section>
<p class="note"><a href="../">Read the handbook</a></p>
</main>"""
    return _page("Scenario for Blender: native downloads", body)
