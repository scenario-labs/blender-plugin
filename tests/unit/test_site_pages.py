# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The downloads page shares the handbook's look and shows every release safely."""

import importlib
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def pages(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    return importlib.import_module("site_pages")


def release(version, **fields):
    item = {
        "id": "scenario",
        "name": "Scenario",
        "version": version,
        "archive_url": f"./scenario-{version}.zip",
        "archive_size": 18869233,
        "archive_hash": "sha256:" + "ab" * 32,
        "blender_version_min": "5.0.0",
        "platforms": ["linux-x64", "windows-x64", "macos-arm64", "macos-x64"],
    }
    item.update(fields)
    return item


class Links(HTMLParser):
    """Collect the text of links inside the element with the given class."""

    def __init__(self, container):
        super().__init__()
        self.container, self.depth, self.inside, self.texts = container, 0, False, []

    def handle_starttag(self, tag, attrs):
        if self.depth:
            self.depth += 1
        elif self.container in (dict(attrs).get("class") or "").split():
            self.depth = 1
        if self.depth and tag == "a":
            self.inside = True
            self.texts.append("")

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1
        if tag == "a":
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.texts[-1] += data.strip()


def nav(page):
    parser = Links("site-nav")
    parser.feed(page)
    return parser.texts


def test_downloads_lists_releases_newest_first_with_their_checks(pages):
    index = {"data": [release("0.10.0"), release("0.9.9"), release("0.11.0")]}

    page = pages.downloads_page(index)

    order = [page.index(f"Scenario {version}") for version in ("0.11.0", "0.10.0", "0.9.9")]
    assert order == sorted(order)
    assert page.count('class="latest"') == 1
    assert page.index('class="latest"') < order[1]
    assert 'href="./scenario-0.11.0.zip"' in page
    assert "ab" * 32 in page and "sha256:" not in page
    assert "18.9 MB" in page
    assert "5.0.0 or newer" in page
    assert "macOS Apple silicon" in page
    assert 'href="../#verify-your-download"' in page


def test_downloads_shows_an_upper_blender_bound(pages):
    page = pages.downloads_page({"data": [release("1.0.0", blender_version_max="5.2.0")]})

    assert "5.0.0 to 5.2.0 (exclusive)" in page


def test_downloads_offers_the_repository_address_to_copy(pages):
    page = pages.downloads_page({"data": [release("1.0.0")]})

    url = "https://blender.scenario.com/repo/index.json"
    assert f'data-copy="{url}"' in page
    assert f"<code>{url}</code>" in page
    assert 'href="./index.json"' in page


def test_downloads_escapes_every_index_value(pages):
    hostile = '"><script>alert(1)</script>'
    page = pages.downloads_page(
        {
            "data": [
                release(
                    "1.0.0" + hostile,
                    name="Scenario" + hostile,
                    archive_url="./x.zip" + hostile,
                    archive_hash="sha256:" + hostile,
                    blender_version_min="5.0.0" + hostile,
                    platforms=["linux-x64" + hostile],
                )
            ]
        }
    )

    assert "<script>alert(1)" not in page
    assert page.count("<script>") == pages.downloads_page({"data": [release("1.0.0")]}).count(
        "<script>"
    )


def test_pages_inline_the_shared_style_and_wordmark(pages):
    for page in (pages.downloads_page({"data": [release("1.0.0")]}), pages.pending_page()):
        style = (ROOT / "docs/site.css").read_text(encoding="utf-8")
        assert f"<style>{style}</style>" in page
        assert 'src="data:image/svg+xml;base64,' in page
        external = set(re.findall(r'(?:src|href)="(https?://[^/"]+)', page))
        assert external <= {
            "https://fonts.googleapis.com",
            "https://fonts.gstatic.com",
            "https://blender.scenario.com",
            "https://github.com",
            "https://app.scenario.com",
        }


def test_pages_share_the_handbook_navigation(pages):
    template = (ROOT / "docs/handbook-template.html").read_text(encoding="utf-8")

    assert nav(pages.downloads_page({"data": [release("1.0.0")]})) == nav(template)
    assert nav(pages.pending_page()) == nav(template)


def test_pages_count_visits_and_download_clicks_like_the_handbook(pages):
    template = (ROOT / "docs/handbook-template.html").read_text(encoding="utf-8")
    page = pages.downloads_page({"data": [release("1.0.0")]})

    assert pages.ANALYTICS in template
    assert pages.ANALYTICS in page and pages.ANALYTICS in pages.pending_page()
    assert 'href="./scenario-1.0.0.zip" data-track="Download"' in page
    assert 'closest("a[data-track]")' in page


def test_pages_inline_the_light_and_dark_favicons(pages):
    for page in (pages.downloads_page({"data": [release("1.0.0")]}), pages.pending_page()):
        icons = re.findall(
            r"<link rel=\"(icon|apple-touch-icon)\" href=\"data:image/png;base64,[^\"]+\"([^>]*)>",
            page,
        )
        assert len(icons) == 7
        assert sum("prefers-color-scheme: dark" in extra for _rel, extra in icons) == 3
        assert sum(rel == "apple-touch-icon" for rel, _extra in icons) == 1


def test_handbook_template_declares_the_same_favicons():
    template = (ROOT / "docs/handbook-template.html").read_text(encoding="utf-8")

    for name in (
        "favicon-16x16.png",
        "favicon-32x32.png",
        "favicon-196x196.png",
        "favicon-dark-16x16.png",
        "favicon-dark-32x32.png",
        "favicon-dark-196x196.png",
        "apple-touch-icon.png",
    ):
        assert f'href="images/{name}"' in template, name


def test_pending_page_explains_that_downloads_follow_the_first_release(pages):
    page = pages.pending_page()

    assert "first verified release" in page
    assert 'href="https://github.com/scenario-labs/blender-plugin/releases"' in page
    assert 'class="releases"' not in page
