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
    parser.add_argument("--inventory", required=True, type=Path, help="Verified release inventory")
    parser.add_argument("--output", type=Path, default=ROOT / "site", help="New site directory")
    parser.add_argument("--source", type=Path, default=ROOT / "docs/USER_GUIDE.md")
    parser.add_argument("--template", type=Path, default=ROOT / "docs/handbook-template.html")
    parser.add_argument("--manifest", type=Path, default=ROOT / "scenario/blender_manifest.toml")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        require_new_output(args.output)
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
