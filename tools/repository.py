# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate an offline native repository from an explicit inventory of exact ZIPs."""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from blender_env import find_blender, inspect_zip, sha256
from build import Session, arguments
from wheel_bundle import validate_bundle

_VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_MANIFEST_FIELDS = (
    "schema_version",
    "id",
    "version",
    "name",
    "tagline",
    "maintainer",
    "type",
    "license",
    "blender_version_min",
    "blender_version_max",
    "website",
    "copyright",
    "tags",
    "permissions",
    "platforms",
)


def version(value):
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise ValueError("Use stable three-component versions without prerelease/build suffixes")
    return tuple(map(int, value.split(".")))


def read_inventory(path):
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Repository inventory is too large")
    inventory = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict) or set(inventory) != {
        "schema_version",
        "extension_id",
        "archives",
    }:
        raise ValueError("Invalid repository inventory fields")
    if type(inventory["schema_version"]) is not int or inventory["schema_version"] != 1:
        raise ValueError("Unsupported repository inventory version")
    identifier = inventory["extension_id"]
    if not isinstance(identifier, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", identifier):
        raise ValueError("Invalid inventory extension identity")
    archives = inventory["archives"]
    if not isinstance(archives, list) or not 1 <= len(archives) <= 100:
        raise ValueError("Inventory must contain between 1 and 100 archives")
    names = set()
    for archive in archives:
        if not isinstance(archive, dict) or set(archive) != {"file", "version", "sha256", "size"}:
            raise ValueError("Invalid archive inventory fields")
        name = archive["file"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.zip", name):
            raise ValueError("Archive file must be a plain ZIP filename")
        if name.casefold() in names:
            raise ValueError("Duplicate archive filename")
        names.add(name.casefold())
        version(archive["version"])
        digest = archive["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Archive SHA-256 must be 64 lowercase hexadecimal characters")
        if type(archive["size"]) is not int or not 1 <= archive["size"] <= 256 * 1024 * 1024:
            raise ValueError("Archive size must be positive and at most 256 MiB")
    return {**inventory, "archives": sorted(archives, key=lambda item: item["file"])}


def verify_bytes(path, archive):
    if not path.is_file() or path.is_symlink():
        raise ValueError("Archive must be an existing regular file")
    if path.stat().st_size != archive["size"] or sha256(path) != archive["sha256"]:
        raise ValueError("Archive size or SHA-256 does not match the inventory")


def python_versions(wheels):
    """Describe the CPython/pure-Python wheel tags used by native repositories."""
    versions = set()
    for wheel in wheels:
        parts = Path(wheel).name.removesuffix(".whl").split("-")
        if len(parts) not in {5, 6}:
            raise ValueError("Unsupported wheel filename in repository archive")
        stable = {tag[3:] for tag in parts[-2].split(".") if re.fullmatch(r"abi[3-9]", tag)}
        if stable:
            versions.update((int(major),) for major in stable)
            continue
        for tag in parts[-3].split("."):
            match = re.fullmatch(r"(?:cp|py)([0-9])([0-9]*)", tag)
            if match is None:
                raise ValueError("Unsupported Python wheel tag in repository archive")
            if int(match[1]) >= 3:
                versions.add((int(match[1]), int(match[2])) if match[2] else (int(match[1]),))
    versions -= {(item[0],) for item in versions if len(item) == 2}
    return [".".join(map(str, item)) for item in sorted(versions)]


def compatibility(manifest):
    minimum = version(manifest["blender_version_min"])
    maximum = (
        version(manifest["blender_version_max"]) if "blender_version_max" in manifest else None
    )
    if maximum is not None and maximum <= minimum:
        raise ValueError("Blender compatibility range is empty")
    platforms = manifest.get("platforms")
    if platforms is not None and (
        not isinstance(platforms, list)
        or not platforms
        or any(not isinstance(value, str) or not value for value in platforms)
        or len(set(platforms)) != len(platforms)
    ):
        raise ValueError("Invalid archive platforms")
    return minimum, maximum, set(platforms or ())


def reject_overlaps(manifests):
    ranges = [compatibility(manifest) for manifest in manifests]
    for position, (minimum, maximum, platforms) in enumerate(ranges):
        for other_min, other_max, other_platforms in ranges[:position]:
            shared_platform = not platforms or not other_platforms or platforms & other_platforms
            shared_version = (maximum is None or other_min < maximum) and (
                other_max is None or minimum < other_max
            )
            if shared_platform and shared_version:
                raise ValueError(
                    "Ambiguous overlapping Blender/platform compatibility in inventory"
                )


def verify_index(repository, inventory, manifests):
    index = json.loads((repository / "index.json").read_text(encoding="utf-8"))
    if not isinstance(index, dict) or index.get("version") != "v1" or index.get("blocklist") != []:
        raise ValueError("Unexpected native repository index")
    rows = index.get("data")
    if not isinstance(rows, list) or len(rows) != len(inventory["archives"]):
        raise ValueError("Native repository omitted or added an archive")
    expected = {
        "./" + item["file"]: (item, manifest)
        for item, manifest in zip(inventory["archives"], manifests, strict=True)
    }
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("archive_url"), str):
            raise ValueError("Invalid native archive entry")
        url = row["archive_url"]
        if url not in expected or url in seen:
            raise ValueError("Native archive URL does not identify exactly one inventory file")
        seen.add(url)
        archive, manifest = expected[url]
        verify_bytes(repository / archive["file"], archive)
        for field in _MANIFEST_FIELDS:
            if row.get(field) != manifest.get(field):
                raise ValueError("Native index differs from archive manifest: " + field)
        if (
            row.get("archive_size") != archive["size"]
            or row.get("archive_hash") != "sha256:" + archive["sha256"]
        ):
            raise ValueError("Native index archive size or hash differs from inventory")
        wheels = manifest.get("wheels", [])
        if row.get("python_versions") != (python_versions(wheels) if wheels else None):
            raise ValueError("Native index Python compatibility differs from archive wheels")
    index["data"] = sorted(rows, key=lambda item: item["archive_url"])
    return index


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_listing(path, index):
    rows = []
    for item in index["data"]:
        blender_range = item["blender_version_min"] + " or newer"
        if "blender_version_max" in item:
            blender_range = (
                item["blender_version_min"] + " to " + item["blender_version_max"] + " (exclusive)"
            )
        cells = [
            '<a href="'
            + html.escape(item["archive_url"], quote=True)
            + '">'
            + html.escape(item["id"] + " " + item["version"])
            + "</a>",
            html.escape(blender_range),
            html.escape(", ".join(item.get("platforms", ["all"]))),
            str(item["archive_size"]),
            html.escape(item["archive_hash"]),
        ]
        rows.append("<tr>" + "".join("<td>" + value + "</td>" for value in cells) + "</tr>")
    path.write_text(
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Extension repository</title></head><body><h1>Extension repository</h1>"
        '<p><a href="./index.json">Blender repository index</a></p><table>'
        "<thead><tr><th>Extension</th><th>Blender versions</th><th>Platforms</th>"
        "<th>Bytes</th><th>SHA-256</th></tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table></body></html>\n",
        encoding="utf-8",
    )


def generate(session, inventory_path, output):
    inventory_path, output = inventory_path.resolve(), output.absolute()
    inventory = read_inventory(inventory_path)
    if output.exists() or output.is_symlink():
        raise ValueError("Repository output already exists; select a new snapshot directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".repository-", dir=output.parent) as temporary:
        repository = Path(temporary) / "repository"
        repository.mkdir()
        manifests = []
        for number, archive in enumerate(inventory["archives"]):
            source = inventory_path.parent / archive["file"]
            verify_bytes(source, archive)
            candidate = repository / archive["file"]
            shutil.copyfile(source, candidate)
            verify_bytes(candidate, archive)
            manifest, _ = inspect_zip(candidate)
            if (
                manifest["id"] != inventory["extension_id"]
                or manifest["version"] != archive["version"]
            ):
                raise ValueError("Archive identity or version differs from inventory")
            # The native generator applies these overrides for split archives.
            generated = manifest.get("build", {}).get("generated", {})
            for field in ("platforms", "wheels"):
                if field in generated:
                    manifest[field] = generated[field]
            compatibility(manifest)
            validate_bundle(candidate)
            session.step(
                f"validate-{number:03}",
                ["--offline-mode", "--command", "extension", "validate", str(candidate)],
            )
            manifests.append(manifest)
        reject_overlaps(manifests)
        session.step(
            "repository",
            [
                "--offline-mode",
                "--command",
                "extension",
                "server-generate",
                "--repo-dir",
                str(repository),
            ],
        )
        index = verify_index(repository, inventory, manifests)
        write_json(repository / "index.json", index)
        write_json(repository / "inventory.json", inventory)
        write_listing(repository / "index.html", index)
        if output.exists() or output.is_symlink():
            raise ValueError("Repository output appeared during generation")
        repository.rename(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    arguments(parser)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument(
        "--output", required=True, type=Path, help="New repository snapshot directory"
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        session = Session(find_blender(args.blender), args.artifacts, args.timeout)
        output = generate(session, args.inventory, args.output)
        session.cleanup()
        print(f"Verified repository: {output}")
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
        print(f"Repository generation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
