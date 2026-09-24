# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Select an offline repository inventory from published-release snapshots and exact assets."""

import argparse
import datetime
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from repository import (
    compatibility,
    read_archive,
    reject_overlaps,
    verify_bytes,
    version,
    write_json,
)

REPOSITORY = "scenario-labs/blender-plugin"
PREFIX = "blender-plugin-v"
MAX_METADATA = 1024 * 1024
MAX_ARCHIVE = 256 * 1024 * 1024


def read_local(path, limit):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= limit:
        raise ValueError("Metadata must be a nonempty bounded regular file")
    with path.open("rb") as handle:
        content = handle.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Metadata exceeds its size limit")
    return content


def published_releases(path):
    """Read the complete `gh api --paginate --slurp` export, never query GitHub."""
    pages = json.loads(read_local(path, 10 * MAX_METADATA))
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ValueError("Use the paginated GitHub release snapshot")
    if sum(map(len, pages)) > 1000:
        raise ValueError("Release snapshot contains too many records")
    releases, seen = [], set()
    for page in pages:
        for release in page:
            if not isinstance(release, dict):
                raise ValueError("Invalid release record")
            tag = release.get("tag_name")
            if not isinstance(tag, str):
                raise ValueError("Invalid release tag")
            if not tag.startswith(PREFIX):
                continue  # Prototype tags never enter the adopted release channel.
            if any(type(release.get(key)) is not bool for key in ("draft", "prerelease")):
                raise ValueError("Release channel flags must be explicit booleans")
            if release["draft"] or release["prerelease"]:
                continue
            release_version = tag.removeprefix(PREFIX)
            version(release_version)
            if release_version in seen:
                raise ValueError("Duplicate stable release version")
            seen.add(release_version)
            if release.get("html_url") != f"https://github.com/{REPOSITORY}/releases/tag/{tag}":
                raise ValueError("Release snapshot belongs to another repository or tag")
            published = release.get("published_at")
            try:
                stamp = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
            except (AttributeError, TypeError, ValueError):
                raise ValueError("Stable release must have a publication timestamp") from None
            if stamp.tzinfo is None:
                raise ValueError("Publication timestamp must include a time zone")
            releases.append(release)
    if not 1 <= len(releases) <= 100:
        raise ValueError("Snapshot must contain between 1 and 100 published stable releases")
    return sorted(releases, key=lambda item: version(item["tag_name"].removeprefix(PREFIX)))


def asset_metadata(release, name, limit):
    assets = release.get("assets")
    if not isinstance(assets, list) or not 1 <= len(assets) <= 100:
        raise ValueError("Release has no bounded asset list")
    if any(not isinstance(asset, dict) for asset in assets):
        raise ValueError("Invalid release asset")
    matches = [asset for asset in assets if asset.get("name") == name]
    if len(matches) != 1:
        raise ValueError("Release must contain exactly one expected archive and checksum asset")
    asset = matches[0]
    tag = release["tag_name"]
    expected_url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
    if asset.get("state") != "uploaded" or asset.get("browser_download_url") != expected_url:
        raise ValueError("Release asset is not uploaded at its canonical destination")
    size = asset.get("size")
    if type(size) is not int or not 1 <= size <= limit:
        raise ValueError("Release asset has an invalid or excessive size")
    return asset


def checksums(path, size):
    raw = read_local(path, MAX_METADATA)
    if len(raw) != size:
        raise ValueError("Checksum file size differs from release metadata")
    rows, seen = {}, set()
    for line in raw.decode("ascii").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64}) [ *]([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if match is None or match[2].casefold() in seen:
            raise ValueError("Invalid or duplicate checksum entry")
        seen.add(match[2].casefold())
        rows[match[2]] = match[1]
    return rows


def candidates(snapshot, assets):
    if not assets.is_dir() or assets.is_symlink():
        raise ValueError("Use an existing nonsymlink asset directory")
    result = []
    for release in published_releases(snapshot):
        tag = release["tag_name"]
        release_version = tag.removeprefix(PREFIX)
        name = f"scenario-{release_version}.zip"
        archive_asset = asset_metadata(release, name, MAX_ARCHIVE)
        checksum_asset = asset_metadata(release, "SHA256SUMS", MAX_METADATA)
        directory = assets / tag
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Each published release needs its own nonsymlink asset directory")
        hashes = checksums(directory / "SHA256SUMS", checksum_asset["size"])
        if name not in hashes:
            raise ValueError("Published checksum file does not identify the expected archive")
        archive = {
            "file": name,
            "version": release_version,
            "sha256": hashes[name],
            "size": archive_asset["size"],
        }
        source = directory / name
        manifest = read_archive(source, archive, "scenario")
        result.append((archive, manifest, source))
    return result


def select(catalog, blender_versions, platforms):
    if not blender_versions or not platforms:
        raise ValueError("Specify the supported Blender versions and platforms explicitly")
    versions = {version(value) for value in blender_versions}
    if any(value < (5, 0, 0) for value in versions):
        raise ValueError("The adopted release channel requires Blender 5.0 or newer")
    if any(not re.fullmatch(r"[a-z]+-[a-z0-9_]+", value) for value in platforms):
        raise ValueError("Use explicit Blender platform identifiers")
    selected = {}
    for blender in sorted(versions):
        for platform in sorted(set(platforms)):
            compatible = []
            for archive, manifest, source in catalog:
                minimum, maximum, supported = compatibility(manifest)
                if (
                    minimum <= blender
                    and (maximum is None or blender < maximum)
                    and (not supported or platform in supported)
                ):
                    compatible.append((archive, manifest, source))
            if not compatible:
                raise ValueError(
                    "Published archives do not cover every requested Blender/platform pair"
                )
            latest = max(compatible, key=lambda item: version(item[0]["version"]))
            selected[latest[0]["file"]] = latest
    retained = [selected[name] for name in sorted(selected)]
    reject_overlaps([item[1] for item in retained])
    return retained


def prepare(snapshot, assets, output, blender_versions, platforms):
    """Copy selected exact bytes atomically; never rebuild, download or publish."""
    if output.exists() or output.is_symlink():
        raise ValueError("Inventory output already exists; choose a new directory")
    retained = select(candidates(snapshot, assets), blender_versions, platforms)
    inventory = {
        "schema_version": 1,
        "extension_id": "scenario",
        "archives": [item[0] for item in retained],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".release-inventory-", dir=output.parent) as temporary:
        staged = Path(temporary) / "selected"
        staged.mkdir()
        for archive, _, source in retained:
            target = staged / archive["file"]
            shutil.copyfile(source, target)
            verify_bytes(target, archive)
        write_json(staged / "inventory.json", inventory)
        if output.exists() or output.is_symlink():
            raise ValueError("Inventory output appeared during preparation")
        staged.rename(output)
    return output / "inventory.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--releases", required=True, type=Path, help="Complete paginated release JSON"
    )
    parser.add_argument("--assets", required=True, type=Path, help="Local release-tag directories")
    parser.add_argument("--output", required=True, type=Path, help="New selected-assets directory")
    parser.add_argument("--blender-version", required=True, action="append")
    parser.add_argument("--platform", required=True, action="append")
    args = parser.parse_args()
    try:
        output = prepare(
            args.releases, args.assets, args.output, args.blender_version, args.platform
        )
        print(f"Selected inventory: {output}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f"Release inventory failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
