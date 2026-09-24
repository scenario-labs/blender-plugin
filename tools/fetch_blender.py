# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fetch a SHA-256-verified Linux/Windows x64 or macOS arm64 Blender into a local cache."""

import argparse
import json
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

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


def extract_windows(archive, staged):
    """Reject ambiguous Windows paths before extracting a verified official ZIP."""
    with zipfile.ZipFile(archive) as bundle:
        seen = set()
        for entry in bundle.infolist():
            name = PurePosixPath(entry.filename)
            normalized = entry.filename.rstrip("/").casefold()
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in entry.filename
                or ":" in entry.filename
                or normalized in seen
                or stat.S_ISLNK(entry.external_attr >> 16)
                or any(part.endswith((".", " ")) for part in name.parts)
            ):
                raise ValueError("Unsafe or ambiguous Blender ZIP member")
            seen.add(normalized)
        bundle.extractall(staged)


def error_message(error):
    """Keep primary and cleanup diagnostics together in the CLI's plain output."""
    return "\n".join([str(error), *getattr(error, "__notes__", [])])


def disk_command(*arguments):
    """Preserve captured disk-tool diagnostics on command failure or timeout."""
    try:
        subprocess.run(
            ["/usr/bin/hdiutil", *arguments], check=True, capture_output=True, timeout=120
        )
    except subprocess.SubprocessError as error:
        diagnostic = getattr(error, "stderr", None)
        if diagnostic:
            if isinstance(diagnostic, bytes):
                diagnostic = diagnostic.decode("utf-8", errors="replace")
            error.add_note(f"hdiutil: {diagnostic.strip()}")
        raise


def extract_macos(archive, staged):
    """Copy Blender.app from a private read-only mount, detaching before publication."""
    # Keep the mount outside the installation TemporaryDirectory: if the OS
    # refuses both detach attempts, cleanup must never walk a mounted volume.
    mount = Path(tempfile.mkdtemp(prefix="scenario-blender-dmg-"))
    attached = False
    primary_error = None
    try:
        disk_command(
            "attach",
            "-readonly",
            "-nobrowse",
            "-noautoopen",
            "-mountpoint",
            str(mount),
            str(archive),
        )
        attached = True
        app = mount / "Blender.app"
        if app.is_symlink() or not app.is_dir():
            raise ValueError("Official disk image did not contain Blender.app")
        shutil.copytree(app, staged / "Blender.app", symlinks=True)
    except BaseException as error:
        # Re-raise interrupts too, after cleanup, without replacing their cause.
        primary_error = error
        raise
    finally:
        try:
            if attached or mount.is_mount():
                try:
                    disk_command("detach", str(mount))
                except (OSError, subprocess.SubprocessError) as first_error:
                    try:
                        # Only this invocation's private read-only mount is targeted.
                        disk_command("detach", "-force", str(mount))
                    except (OSError, subprocess.SubprocessError) as force_error:
                        force_error.add_note(f"Initial detach failed: {error_message(first_error)}")
                        raise
            mount.rmdir()
        except (OSError, subprocess.SubprocessError) as cleanup_error:
            if primary_error is None:
                raise
            primary_error.add_note(f"Disk image cleanup failed: {error_message(cleanup_error)}")


def install_archive(archive, installation, temporary, expected, version, platform_name="linux-x64"):
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
    if platform_name == "windows-x64":
        extract_windows(archive, staged)
        relative_binary = Path(f"blender-{version}-{platform_name}") / "blender.exe"
    elif platform_name == "macos-arm64":
        extract_macos(archive, staged)
        relative_binary = Path("Blender.app/Contents/MacOS/Blender")
    else:
        with tarfile.open(archive, "r:xz") as bundle:
            bundle.extractall(staged, filter="data")
        relative_binary = Path(f"blender-{version}-{platform_name}") / "blender"
    binary = staged / relative_binary
    if not binary.is_file() or not binary.resolve().is_relative_to(staged.resolve()):
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


def fetch(version, cache, expected=None, *, platform_name="linux-x64"):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Use a full Blender version, for example 5.0.1")
    expected = expected or None
    if expected and not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
        raise ValueError("--sha256 must contain 64 hexadecimal characters")
    suffixes = {"linux-x64": "tar.xz", "windows-x64": "zip", "macos-arm64": "dmg"}
    if platform_name not in suffixes:
        raise ValueError("Automatic download supports Linux/Windows x64 and macOS arm64")
    suffix = suffixes[platform_name]
    filename = f"blender-{version}-{platform_name}.{suffix}"
    slot = version if platform_name == "linux-x64" else f"{version}-{platform_name}"
    series = version.rsplit(".", 1)[0]
    base = f"https://download.blender.org/release/Blender{series}"
    cache = cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    with (
        installation_lock(cache, slot),
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
        installation = cache / f"{slot}-{expected}"
        binary = install_archive(archive, installation, temporary, expected, version, platform_name)
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
    system, machine = platform.system(), platform.machine().lower()
    if system in {"Linux", "Windows"} and machine in {"x86_64", "amd64"}:
        platform_name = f"{system.lower()}-x64"
    elif system == "Darwin" and machine in {"arm64", "aarch64"}:
        platform_name = "macos-arm64"
    else:
        parser.error(
            "Automatic download supports Linux/Windows x64 and macOS arm64; "
            "install Blender and set BLENDER on this platform"
        )
    try:
        fetch(args.version, args.cache, args.sha256, platform_name=platform_name)
        return 0
    except (
        OSError,
        ValueError,
        tarfile.TarError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as error:
        print(f"Download failed: {error_message(error)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
