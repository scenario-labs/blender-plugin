# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline handbook output, input failures and filesystem boundaries."""

import base64

import pytest

from tools.build_docs_html import HandbookError, build_handbook, main

TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Handbook</title></head><body><nav>{{toc}}</nav>
<main>{{content}}</main><footer>{{version}}</footer></body></html>"""
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII="
)


@pytest.fixture
def inputs(tmp_path):
    docs = tmp_path / "docs"
    (docs / "images").mkdir(parents=True)
    (docs / "images/panel.png").write_bytes(PNG)
    source = docs / "guide.md"
    source.write_text(
        '# Guide\n\n## Install\n\n![The Scenario settings panel](images/panel.png "Settings")\n'
        "\n## Install\n\n| Option | Value |\n| --- | --- |\n| Online | On |\n"
        '\n```python\nprint("hello")\n```\n'
    )
    template = docs / "template.html"
    template.write_text(TEMPLATE)
    manifest = tmp_path / "manifest.toml"
    manifest.write_text('version = "1.2.3"\n')
    return {
        "source": source,
        "template": template,
        "manifest": manifest,
        "output": tmp_path / "site/index.html",
        "root": tmp_path,
    }


def test_website_copies_exact_images_and_renders_metadata_toc_tables_and_code(inputs):
    output = build_handbook(**inputs)
    text = output.read_text()
    assert text.startswith("<!DOCTYPE html>")
    for fragment in (
        '<html lang="en">',
        '<meta charset="utf-8">',
        "<title>Handbook</title>",
        '<a href="#install">Install</a>',
        '<h2 id="install_1">Install</h2>',
        "<table>",
        '<code class="language-python">',
        'alt="The Scenario settings panel"',
        'title="Settings"',
        "<footer>1.2.3</footer>",
    ):
        assert fragment in text
    assert "{{" not in text
    assert "data:image" not in text
    assert (output.parent / "images/panel.png").read_bytes() == PNG
    (inputs["source"].parent / "images/unreferenced.png").write_bytes(PNG)
    build_handbook(**inputs)
    assert output.read_text() == text
    assert not (output.parent / "images/unreferenced.png").exists()


def test_standalone_embeds_exact_image_without_copying_files(inputs):
    output = build_handbook(**inputs, inline_images=True)
    assert f"data:image/png;base64,{base64.b64encode(PNG).decode()}" in output.read_text()
    assert not (output.parent / "images").exists()


@pytest.mark.parametrize(
    "url",
    [
        "images/missing.png",
        "https://example.invalid/panel.png",
        "../panel.png",
        "/tmp/panel.png",
        "images/panel.png?token=secret",
        "images/panel.png#fragment",
        "images%2f..%2f..%2fpanel.png",
        "images%5cpanel.png",
    ],
)
def test_rejects_missing_remote_and_escaping_images_without_writing_output(inputs, url):
    inputs["source"].write_text(f"![Useful panel description]({url})")
    with pytest.raises(HandbookError):
        build_handbook(**inputs)
    assert not inputs["output"].parent.exists()


@pytest.mark.parametrize(
    "image",
    [
        "![](images/panel.png)",
        '<img src="images/panel.png" alt="   ">',
        '<img alt="Useful description" src="images/panel.png" srcset="remote.png 2x">',
    ],
)
def test_markdown_and_raw_images_require_alt_and_one_explicit_file(inputs, image):
    inputs["source"].write_text(image)
    with pytest.raises(HandbookError):
        build_handbook(**inputs)
    assert not inputs["output"].exists()


def test_empty_image_is_rejected(inputs):
    (inputs["source"].parent / "images/panel.png").write_bytes(b"")
    with pytest.raises(HandbookError, match="Empty image"):
        build_handbook(**inputs)


def test_image_symlink_cannot_escape_source_directory(inputs):
    image = inputs["source"].parent / "images/panel.png"
    image.unlink()
    outside = inputs["root"] / "outside.png"
    outside.write_bytes(PNG)
    try:
        image.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Host cannot create symlinks: {error}")
    with pytest.raises(HandbookError, match="outside"):
        build_handbook(**inputs)


def test_output_image_symlink_cannot_write_outside_output_directory(inputs):
    inputs["output"].parent.mkdir()
    outside = inputs["root"] / "outside"
    outside.mkdir()
    try:
        (inputs["output"].parent / "images").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Host cannot create symlinks: {error}")
    with pytest.raises(HandbookError, match="destination"):
        build_handbook(**inputs)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    "before,after",
    [
        ("{{content}}", "{{unknown}}"),
        ("{{toc}}", "{{toc}}{{toc}}"),
        ("{{version}}", ""),
        ('<meta charset="utf-8">', ""),
        ('<html lang="en">', "<html>"),
        ("<title>Handbook</title>", ""),
        ("<title>Handbook</title>", "<title> </title>"),
        ("<!DOCTYPE html>", ""),
        ('<meta name="viewport" content="width=device-width, initial-scale=1">', ""),
    ],
)
def test_template_requires_known_slots_and_document_metadata(inputs, before, after):
    inputs["template"].write_text(TEMPLATE.replace(before, after))
    with pytest.raises(HandbookError):
        build_handbook(**inputs)
    assert not inputs["output"].exists()


def test_source_cannot_leave_unresolved_slots(inputs):
    inputs["source"].write_text("# Guide\n\n{{missing}}")
    with pytest.raises(HandbookError, match="unresolved"):
        build_handbook(**inputs)


@pytest.mark.parametrize("version", ['"1.2"', "123", '"1.2.3<script>"'])
def test_manifest_version_is_validated(inputs, version):
    inputs["manifest"].write_text(f"version = {version}")
    with pytest.raises(HandbookError, match="version"):
        build_handbook(**inputs)


@pytest.mark.parametrize("input_name", ["source", "template", "manifest"])
def test_output_cannot_overwrite_input(inputs, input_name):
    original = inputs[input_name].read_bytes()
    inputs["output"] = inputs[input_name]
    with pytest.raises(HandbookError, match="overwrite"):
        build_handbook(**inputs)
    assert inputs[input_name].read_bytes() == original


def test_relative_links_point_to_repository_and_fragments_stay_local(inputs):
    (inputs["source"].parent / "More notes.md").write_text("# Details")
    inputs["source"].write_text(
        "[Notes](<More notes.md#details>)\n\n[Install](#install)\n\n[External](https://example.invalid/)"
    )
    text = build_handbook(**inputs).read_text()
    assert (
        'href="https://github.com/scenario-labs/blender-plugin/blob/main/docs/More%20notes.md#details"'
        in text
    )
    assert 'href="#install"' in text
    assert 'href="https://example.invalid/"' in text


@pytest.mark.parametrize(
    "link", ["missing.md", "../../outside.md", "javascript:alert", "//example.invalid/x"]
)
def test_unresolvable_or_unsafe_links_fail(inputs, link):
    inputs["source"].write_text(f"[Link]({link})")
    with pytest.raises(HandbookError):
        build_handbook(**inputs)


def test_image_names_with_spaces_are_encoded_without_changing_bytes(inputs):
    image = inputs["source"].parent / "images/panel.png"
    image.rename(image.with_name("panel detail.png"))
    inputs["source"].write_text("![Panel detail](<images/panel detail.png>)")
    output = build_handbook(**inputs)
    assert 'src="images/panel%20detail.png"' in output.read_text()
    assert (output.parent / "images/panel detail.png").read_bytes() == PNG


def test_cli_reports_invalid_input_without_success_artifact(inputs, capsys):
    inputs["template"].write_text("{{content}}")
    with pytest.raises(SystemExit) as error:
        main(
            [
                "--source",
                str(inputs["source"]),
                "--template",
                str(inputs["template"]),
                "--manifest",
                str(inputs["manifest"]),
                "--output",
                str(inputs["output"]),
            ]
        )
    assert error.value.code == 1
    assert "Handbook error:" in capsys.readouterr().err
    assert not inputs["output"].exists()


def test_prerelease_manifest_version_is_preserved(inputs):
    inputs["manifest"].write_text('version = "1.2.3-rc.1"')
    assert "<footer>1.2.3-rc.1</footer>" in build_handbook(**inputs).read_text()
