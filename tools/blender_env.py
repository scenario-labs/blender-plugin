# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable Blender discovery and exact installed-package verification (stdlib only)."""

import argparse
import hashlib
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

if __package__:
    from . import zip_limits
else:
    import zip_limits

ROOT = Path(__file__).resolve().parents[1]


def _version_key(path):
    """Sort versioned installation paths numerically, including multi-digit releases."""
    for part in reversed(path.parts):
        match = re.search(r"(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?", part)
        if match:
            return tuple(int(value or 0) for value in match.groups()), str(path)
    return (0, 0, 0), str(path)


def manifest_version():
    """Read the extension version without discovering or launching Blender."""
    manifest = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("The extension manifest must contain a version string")
    return version


def find_blender(explicit=None):
    selected = explicit or os.environ.get("BLENDER")
    if selected:
        candidate = shutil.which(selected) or str(Path(selected).expanduser())
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return Path(candidate).resolve()
        raise ValueError("Blender not found: set BLENDER=/path/to/blender or use --blender PATH")
    found = shutil.which("blender")
    if found:
        return Path(found).resolve()
    candidates = []
    system = platform.system()
    if system == "Darwin":
        candidates = [
            Path("/Applications/Blender.app/Contents/MacOS/Blender"),
            *sorted(
                [
                    *Path("/Applications").glob("Blender*.app/Contents/MacOS/Blender"),
                    *Path("/Applications").glob("Blender*/Blender.app/Contents/MacOS/Blender"),
                ],
                key=_version_key,
                reverse=True,
            ),
        ]
    elif system == "Windows":
        candidates = sorted(
            Path("C:/Program Files/Blender Foundation").glob("Blender*/blender.exe"),
            key=_version_key,
            reverse=True,
        )
    else:
        candidates = [
            Path("/snap/bin/blender"),
            Path("/usr/bin/blender"),
            *sorted(Path("/opt").glob("blender*/blender"), key=_version_key, reverse=True),
        ]
    for folder in sorted((ROOT / ".blender").glob("*"), key=_version_key, reverse=True):
        if not folder.is_dir():
            continue
        if system == "Darwin":
            candidates.append(folder / "Blender.app/Contents/MacOS/Blender")
        elif system == "Windows":
            candidates.extend(
                [folder / "blender.exe", *folder.glob("blender-*-windows-x64/blender.exe")]
            )
        else:
            candidates.extend(
                [
                    folder / "blender",
                    *folder.glob("blender-*-linux-x64/blender"),
                ]
            )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise ValueError("Blender not found: set BLENDER=/path/to/blender or use --blender PATH")


def isolated_environment(profile, temporary, environ=None):
    """Do not inherit credentials, source paths, or any user's Blender directory overrides."""
    original = os.environ if environ is None else environ
    env = {
        key: value
        for key, value in original.items()
        if not key.startswith(("SCENARIO_", "BLENDER_", "PYTHON"))
    }
    env["BLENDER_USER_RESOURCES"] = str(Path(profile).resolve())
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in ("TMPDIR", "TEMP", "TMP"):
        env[key] = str(Path(temporary).resolve())
    return env


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def inspect_zip(path):
    """Reject unsafe or ambiguous layouts before Blender installs the archive."""
    files = {}
    with zipfile.ZipFile(path) as archive:
        zip_limits.check_archive(archive)
        manifest = tomllib.loads(
            zip_limits.read_member(
                archive, "blender_manifest.toml", limit=zip_limits.MAX_METADATA_BYTES
            ).decode()
        )
        for entry in archive.infolist():
            name = PurePosixPath(entry.filename)
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in entry.filename
                or ":" in entry.filename
                or entry.filename in files
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError("Unsafe or duplicate extension ZIP member")
            if not entry.is_dir():
                with archive.open(entry) as member:
                    files[entry.filename] = hashlib.file_digest(member, "sha256").hexdigest()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", manifest["id"]):
            raise ValueError("Invalid extension module ID")
        if "LICENSE" not in files or "__init__.py" not in files:
            raise ValueError("Extension ZIP must include LICENSE and __init__.py")
    return manifest, files


def verify_installed(archive_path, package_dir):
    manifest, expected = inspect_zip(archive_path)
    package_dir = Path(package_dir).resolve()
    actual = {}
    for path in package_dir.rglob("*"):
        relative = path.relative_to(package_dir)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("Installed package contains a symlink")
        if path.is_file():
            actual[relative.as_posix()] = sha256(path)
    if actual != expected:
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        changed = sorted(
            name for name in expected.keys() & actual.keys() if expected[name] != actual[name]
        )
        raise ValueError(
            f"Installed package differs from candidate ZIP: missing={missing}, extra={extra}, changed={changed}"
        )
    return manifest


def normal_profile_root():
    """Find the regular profile independently of Blender's isolated environment."""
    if platform.system() == "Darwin":
        return Path.home() / "Library/Application Support/Blender"
    if platform.system() == "Windows":
        return (
            Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
            / "Blender Foundation/Blender"
        )
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "blender"


def profile_snapshot(root):
    """Record file metadata without reading credentials or following directory symlinks."""
    result = {}
    if root.exists():
        for folder, directories, files in os.walk(root, followlinks=False):
            for name in directories + files:
                path = Path(folder) / name
                info = path.lstat()
                result[str(path.relative_to(root))] = (info.st_mode, info.st_size, info.st_mtime_ns)
    return result


def run_step(binary, args, *, env, directory, name, timeout):
    log = directory / f"{name}.log"
    print(f"{name}: {log}", flush=True)
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(
            [str(binary), *args],
            cwd=directory,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, name)
    return log


def main():
    parser = argparse.ArgumentParser(
        description="Print the selected Blender executable path or extension manifest version."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--blender", help="Executable path or command; defaults to BLENDER/discovery"
    )
    selection.add_argument(
        "--version",
        "--manifest-version",
        action="store_true",
        dest="manifest_version",
        help="Print the extension manifest version without launching Blender",
    )
    args = parser.parse_args()
    try:
        value = manifest_version() if args.manifest_version else find_blender(args.blender)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
