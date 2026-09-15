# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fetch an official, SHA-256-verified Linux x64 Blender into a local cache."""

import argparse
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from blender_env import ROOT, sha256


def download(url, destination):
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def checksum(text, filename):
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip("*") == filename:
            if re.fullmatch(r"[a-fA-F0-9]{64}", fields[0]):
                return fields[0].lower()
    raise ValueError("Official checksum file does not contain the requested archive")


def fetch(version, cache, expected=None):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Use a full Blender version, for example 5.0.1")
    if expected and not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
        raise ValueError("--sha256 must contain 64 hexadecimal characters")
    filename = f"blender-{version}-linux-x64.tar.xz"
    series = version.rsplit(".", 1)[0]
    base = f"https://download.blender.org/release/Blender{series}"
    cache = cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fetch-", dir=cache) as temporary:
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
        # Always extract the verified archive afresh, so a modified extracted cache
        # can never bypass verification. Keep each installation independently owned.
        installation = Path(tempfile.mkdtemp(prefix=f"{version}-", dir=cache))
        try:
            with tarfile.open(archive, "r:xz") as bundle:
                bundle.extractall(installation, filter="data")
            binary = installation / f"blender-{version}-linux-x64" / "blender"
            if not binary.is_file():
                raise ValueError("Official archive did not contain the expected Blender executable")
        except Exception:
            shutil.rmtree(installation)
            raise
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
