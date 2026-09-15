# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable Blender discovery and exact installed-package verification (stdlib only)."""

import hashlib
import os
import platform
import re
import shutil
import stat
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def find_blender(explicit=None):
    selected = explicit or os.environ.get("BLENDER")
    if selected:
        candidate = shutil.which(selected) or str(Path(selected).expanduser())
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return Path(candidate).resolve()
        raise ValueError("Blender not found: set BLENDER to an executable or use --blender PATH")
    found = shutil.which("blender")
    if found:
        return Path(found).resolve()
    candidates = []
    if platform.system() == "Darwin":
        candidates = [Path("/Applications/Blender.app/Contents/MacOS/Blender")]
    elif platform.system() == "Windows":
        candidates = sorted(
            Path("C:/Program Files/Blender Foundation").glob("Blender*/blender.exe"), reverse=True
        )
    else:
        candidates = [
            Path("/snap/bin/blender"),
            *sorted(Path("/opt").glob("blender*/blender"), reverse=True),
        ]
    for folder in sorted((ROOT / ".blender").glob("*"), reverse=True):
        candidates.extend(
            [
                folder / "blender",
                folder / "blender.exe",
                folder / "Blender.app/Contents/MacOS/Blender",
            ]
        )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise ValueError("Blender not found: set BLENDER to an executable or use --blender PATH")


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
                files[entry.filename] = hashlib.sha256(archive.read(entry)).hexdigest()
        manifest = tomllib.loads(archive.read("blender_manifest.toml").decode())
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
