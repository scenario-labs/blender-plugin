# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stage a guide and native repository from an explicit inventory of exact release ZIPs.

This offline command neither builds extension archives nor publishes the site.
Release selection and provenance verification precede this build.
"""

import argparse
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from blender_env import ROOT, find_blender
from build import Session, arguments
from build_docs_html import build_handbook
from repository import generate, read_inventory


def require_new_output(output):
    if output.exists() or output.is_symlink():
        raise ValueError("Site output already exists; select a new snapshot directory")


def build_pending_site(output, *, source, template, manifest, root=ROOT):
    """Publish a guide while the adopted release channel is still empty."""
    require_new_output(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".site-", dir=output.parent) as temporary:
        staged = Path(temporary) / "site"
        build_handbook(source, template, manifest, staged / "index.html", root=root)
        if any(path.name.casefold() == "repo" for path in staged.iterdir()):
            raise ValueError("Handbook assets conflict with the reserved repo directory")
        (staged / "repo").mkdir()
        (staged / "repo/index.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Scenario for Blender: native downloads</title>"
            "<body><main><h1>Native downloads are coming</h1>"
            "<p>The official extension repository will become available after the first "
            "verified release. No native update index is published yet.</p>"
            '<p><a href="https://github.com/scenario-labs/blender-plugin/releases">'
            "Download a release ZIP</a> and install it with Blender’s Install from Disk.</p>"
            '<p><a href="../">Read the handbook</a></p></main></body></html>',
            encoding="utf-8",
        )
        require_new_output(output)
        staged.rename(output)
    return output


def build_site(
    session,
    inventory,
    output,
    *,
    source=ROOT / "docs/USER_GUIDE.md",
    template=ROOT / "docs/handbook-template.html",
    manifest=ROOT / "scenario/blender_manifest.toml",
    root=ROOT,
):
    """Expose the complete snapshot only after both existing builders succeed."""
    output = output.absolute()
    require_new_output(output)
    identifier = tomllib.loads(manifest.read_text(encoding="utf-8"))["id"]
    if read_inventory(inventory)["extension_id"] != identifier:
        raise ValueError("Release inventory identity differs from the handbook manifest")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".site-", dir=output.parent) as temporary:
        staged = Path(temporary) / "site"
        build_handbook(source, template, manifest, staged / "index.html", root=root)
        # Image paths are source-relative; reserve repo/ even on case-sensitive hosts.
        if any(path.name.casefold() == "repo" for path in staged.iterdir()):
            raise ValueError("Handbook assets conflict with the reserved repo directory")
        generate(session, inventory, staged / "repo")
        if read_inventory(staged / "repo/inventory.json")["extension_id"] != identifier:
            raise ValueError("Release inventory identity changed during site generation")
        require_new_output(output)
        staged.rename(output)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    arguments(parser)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inventory", type=Path, help="Verified release inventory")
    mode.add_argument(
        "--pending-repository", action="store_true", help="Handbook before first release"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "site", help="New site directory")
    parser.add_argument("--source", type=Path, default=ROOT / "docs/USER_GUIDE.md")
    parser.add_argument("--template", type=Path, default=ROOT / "docs/handbook-template.html")
    parser.add_argument("--manifest", type=Path, default=ROOT / "scenario/blender_manifest.toml")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        require_new_output(args.output)
        if args.pending_repository:
            build_pending_site(
                args.output, source=args.source, template=args.template, manifest=args.manifest
            )
            return 0
        if args.artifacts.resolve().is_relative_to(args.output.resolve()):
            raise ValueError("Blender artifacts must be outside the site output")
        session = Session(find_blender(args.blender), args.artifacts, args.timeout)
        output = build_site(
            session,
            args.inventory,
            args.output,
            source=args.source,
            template=args.template,
            manifest=args.manifest,
        )
        session.cleanup()
        print(f"Verified site: {output}")
        return 0
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 128 - error.returncode
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"Site build failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
