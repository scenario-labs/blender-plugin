# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Discover, download and verify the current published repository inventory.

Run inside the Pages deployment concurrency lock. Never builds release archives
or writes to GitHub. A second complete discovery detects publication races.
"""

import argparse
import json
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from blender_env import ROOT
from release_inventory import (
    MAX_ARCHIVE,
    MAX_METADATA,
    PREFIX,
    REPOSITORY,
    asset_metadata,
    prepare,
    published_releases,
)
from repository import write_json
from verify_release_inventory import GitHub, verify

BLENDER_VERSIONS = ("5.0.0", "5.1.0", "5.2.0")
PLATFORMS = ("linux-x64", "windows-x64", "macos-arm64", "macos-x64")
# This is the last historical release, not a moving "current version" setting.
# Release-please advances the checked-out manifest before the first adopted
# release is published, permanently retiring automatic handbook-only bootstrap.
HANDBOOK_BOOTSTRAP_VERSION = "0.9.9"


def bootstrap_checkout(manifest):
    value = tomllib.loads(manifest.read_text(encoding="utf-8"))
    return value.get("id") == "scenario" and value.get("version") == HANDBOOK_BOOTSTRAP_VERSION


def discover(github, snapshot, *, allow_bootstrap=False):
    snapshot.write_bytes(
        github.run(["api", f"repos/{REPOSITORY}/releases?per_page=100", "--paginate", "--slurp"])
    )
    pages = json.loads(snapshot.read_bytes())
    if allow_bootstrap:
        if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
            raise ValueError("Invalid paginated release snapshot")
        rows = [row for page in pages for row in page]
        if (
            not rows
            or len(rows) > 1000
            or any(
                not isinstance(row, dict) or not isinstance(row.get("tag_name"), str)
                for row in rows
            )
        ):
            raise ValueError("Invalid release metadata")
        # Only the initial channel may publish a handbook without a repository.
        # A draft, prerelease or malformed adopted release must not trigger this path.
        if not any(row["tag_name"].startswith(PREFIX) for row in rows):
            return [], []
    releases = published_releases(snapshot)
    # Ignore mutable descriptions and download counters, retain release/asset identity.
    identity = []
    for release in releases:
        name = f"scenario-{release['tag_name'].removeprefix(PREFIX)}.zip"
        assets = [
            asset_metadata(release, name, MAX_ARCHIVE),
            asset_metadata(release, "SHA256SUMS", MAX_METADATA),
        ]
        identity.append(
            {
                "release": [release.get(k) for k in ("id", "tag_name", "published_at")],
                "assets": [
                    {k: asset.get(k) for k in ("id", "name", "size", "updated_at", "digest")}
                    for asset in assets
                ],
            }
        )
    return releases, identity


def download(github, asset, path):
    identifier = asset.get("id")
    if type(identifier) is not int or identifier < 1:
        raise ValueError("Release asset requires a positive GitHub id")
    content = github.run(
        [
            "api",
            f"repos/{REPOSITORY}/releases/assets/{identifier}",
            "--header",
            "Accept: application/octet-stream",
        ],
        asset["size"],
    )
    if len(content) != asset["size"]:
        raise ValueError("Downloaded asset size differs from release metadata")
    path.write_bytes(content)


def prepare_current(
    output, *, github=None, allow_bootstrap=False, manifest=ROOT / "scenario/blender_manifest.toml"
):
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists")
    github = github or GitHub()
    allow_bootstrap = allow_bootstrap and bootstrap_checkout(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".site-releases-", dir=output.parent) as temporary:
        root = Path(temporary)
        snapshot = root / "releases.json"
        releases, identity = discover(github, snapshot, allow_bootstrap=allow_bootstrap)
        assets = root / "downloads"
        assets.mkdir()
        for release in releases:
            tag = release["tag_name"]
            directory = assets / tag
            directory.mkdir()
            name = f"scenario-{tag.removeprefix(PREFIX)}.zip"
            for filename, limit in ((name, MAX_ARCHIVE), ("SHA256SUMS", MAX_METADATA)):
                download(github, asset_metadata(release, filename, limit), directory / filename)
        if releases:
            selected = prepare(snapshot, assets, root / "selected", BLENDER_VERSIONS, PLATFORMS)
            verified = verify(selected, root / "verified", github=github)
        else:
            (root / "verified").mkdir()
            verified = root / "verified/inventory.json"
        _, current = discover(github, root / "current.json", allow_bootstrap=allow_bootstrap)
        if identity != current:
            raise ValueError("Published releases changed; refresh and retry")
        write_json(verified.parent / "publication.json", identity)
        if output.exists() or output.is_symlink():
            raise ValueError("Output appeared during preparation")
        verified.parent.rename(output)
    return output / "inventory.json" if releases else None


def check_current(directory, *, github=None, manifest=ROOT / "scenario/blender_manifest.toml"):
    """Recheck immediately before deployment, after potentially slow native builds."""
    github = github or GitHub()
    expected = json.loads((directory / "publication.json").read_text())
    with tempfile.TemporaryDirectory(prefix="scenario-site-check-") as temporary:
        _, identity = discover(
            github,
            Path(temporary) / "releases.json",
            allow_bootstrap=not expected and bootstrap_checkout(manifest),
        )
        if identity != expected:
            raise ValueError("Published releases changed after the site build; rerun deployment")
        # Also recheck tag commits and cryptographic provenance of the exact offered bytes.
        if expected:
            verify(directory / "inventory.json", Path(temporary) / "verified", github=github)
            _, current = discover(github, Path(temporary) / "after-verification.json")
            if current != expected:
                raise ValueError("Published releases changed during the final verification")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-current", action="store_true")
    parser.add_argument("--allow-bootstrap", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_current:
            check_current(args.output)
        else:
            prepare_current(args.output, allow_bootstrap=args.allow_bootstrap)
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        print(
            "Site release preparation failed; inspect publication and provenance", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
