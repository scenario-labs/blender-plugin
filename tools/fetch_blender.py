# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fetch an official, SHA-256-verified Linux x64 Blender into a local cache."""

import argparse
import json
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from blender_env import ROOT, sha256


def download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "scenario-blender-tools/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def checksum(text, filename):
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip("*") == filename:
            if re.fullmatch(r"[a-fA-F0-9]{64}", fields[0]):
                return fields[0].lower()
    raise ValueError("Official checksum file does not contain the requested archive")


@contextmanager
def installation_lock(cache, version):
    lock = cache / f".fetch-{version}.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError(
            f"Cache lock exists: {lock}. Remove it only when no fetch is running."
        ) from error
    try:
        yield
    finally:
        lock.rmdir()


def install_archive(archive, installation, temporary, expected, version):
    """Publish a verified extraction in one owned slot; preserve the old one on failure."""
    marker = installation / ".scenario-fetch.json"
    ownership = {"sha256": expected}
    if installation.is_symlink() or (
        installation.exists()
        and (
            marker.is_symlink()
            or not marker.is_file()
            or json.loads(marker.read_text()) != ownership
        )
    ):
        raise ValueError(f"Refusing to replace an unmanaged installation: {installation}")
    staged = temporary / "installation"
    staged.mkdir()
    with tarfile.open(archive, "r:xz") as bundle:
        bundle.extractall(staged, filter="data")
    relative_binary = Path(f"blender-{version}-linux-x64") / "blender"
    if not (staged / relative_binary).is_file():
        raise ValueError("Official archive did not contain the expected Blender executable")
    (staged / marker.name).write_text(json.dumps(ownership))
    previous = temporary / "previous-installation"
    if installation.exists():
        installation.rename(previous)
    try:
        staged.rename(installation)
    except OSError:
        if previous.exists():
            previous.rename(installation)
        raise
    return installation / relative_binary


def fetch(version, cache, expected=None):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Use a full Blender version, for example 5.0.1")
    expected = expected or None
    if expected and not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
        raise ValueError("--sha256 must contain 64 hexadecimal characters")
    filename = f"blender-{version}-linux-x64.tar.xz"
    series = version.rsplit(".", 1)[0]
    base = f"https://download.blender.org/release/Blender{series}"
    cache = cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    with (
        installation_lock(cache, version),
        tempfile.TemporaryDirectory(prefix="fetch-", dir=cache) as temporary,
    ):
        temporary = Path(temporary)
        if expected is None:
            sums = temporary / "checksums"
            download(f"{base}/blender-{version}.sha256", sums)
            expected = checksum(sums.read_text(), filename)
        expected = expected.lower()
        archive = cache / f"{filename}.{expected}"
        if not archive.exists() or sha256(archive) != expected:
            candidate = temporary / filename
            download(f"{base}/{filename}", candidate)
            if sha256(candidate) != expected:
                raise ValueError("Blender archive SHA-256 mismatch")
            candidate.replace(archive)
        # Re-extract from the verified archive, replacing only this tool's owned
        # slot for the same version and checksum. Temporary storage removes the
        # previous extraction after successful publication.
        installation = cache / f"{version}-{expected}"
        binary = install_archive(archive, installation, temporary, expected, version)
    print(binary)
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--sha256", help="Pinned archive digest; otherwise read the official checksum file"
    )
    parser.add_argument("--cache", type=Path, default=ROOT / ".blender")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        parser.error(
            "Automatic download supports Linux x64; install Blender and set BLENDER on this platform"
        )
    try:
        fetch(args.version, args.cache, args.sha256)
        return 0
    except (OSError, ValueError, tarfile.TarError) as error:
        print(f"Download failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
