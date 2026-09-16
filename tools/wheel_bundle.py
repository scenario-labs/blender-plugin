# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stage hash-pinned wheels and their notices without modifying source or profiles."""

import hashlib
import http.client
import io
import json
import re
import shutil
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

if __package__:
    from . import zip_limits
else:
    import zip_limits

LOCK_NAME = "sdk-wheel-lock.json"
DOWNLOAD_ATTEMPTS = 3
RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _safe_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError("Unsafe wheel member path")
    return path


def validate_lock(lock, manifest):
    if (
        lock.get("schema_version") != 1
        or not isinstance(lock.get("wheels"), list)
        or not lock["wheels"]
        or len(lock["wheels"]) > 128
    ):
        raise ValueError("Invalid SDK wheel lock")
    names = set()
    for wheel in lock["wheels"]:
        filename = wheel["filename"]
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", filename) or filename in names:
            raise ValueError("Invalid or duplicate wheel filename")
        names.add(filename)
        if not re.fullmatch(r"[a-f0-9]{64}", wheel["sha256"]):
            raise ValueError("Invalid wheel SHA-256")
        url = urlsplit(wheel["url"])
        if (
            url.scheme != "https"
            or url.netloc != "files.pythonhosted.org"
            or url.query
            or url.fragment
            or not url.path.endswith("/" + filename)
        ):
            raise ValueError("Wheel URL must identify its pinned PyPI artifact")
        if not re.fullmatch(r"[a-z0-9-]+", wheel["package"]):
            raise ValueError("Invalid wheel package name")
        if not wheel["licenses"] or len(wheel["licenses"]) > 32:
            raise ValueError("Invalid wheel license notice count")
        for notice in wheel["licenses"]:
            _safe_path(notice["path"])
            if not re.fullmatch(r"[a-f0-9]{64}", notice["sha256"]):
                raise ValueError("Invalid license SHA-256")
    expected = {"./wheels/" + name for name in names}
    declared = manifest.get("wheels", [])
    if set(declared) != expected or len(declared) != len(expected):
        raise ValueError("Manifest wheels differ from SDK wheel lock")
    if manifest.get("platforms") != lock.get("platforms"):
        raise ValueError("Manifest platforms differ from SDK wheel lock")


def _download(url, path):
    request = urllib.request.Request(
        url, headers={"User-Agent": "scenario-blender-wheel-bundle/1.0"}
    )
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            with (
                urllib.request.urlopen(request, timeout=120) as response,
                path.open("wb") as output,
            ):
                size = 0
                while chunk := response.read(64 * 1024):
                    size += len(chunk)
                    if size > zip_limits.MAX_MEMBER_BYTES:
                        raise ValueError("Downloaded wheel size exceeds limit")
                    output.write(chunk)
            return
        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            http.client.IncompleteRead,
        ) as error:
            path.unlink(missing_ok=True)
            if isinstance(error, urllib.error.HTTPError):
                error.close()
                if error.code not in RETRYABLE_HTTP_STATUS:
                    raise
            if attempt + 1 == DOWNLOAD_ATTEMPTS:
                raise
            time.sleep(2**attempt)


def cached_wheel(wheel, cache, *, offline=False):
    """Verify every reuse; download to a private file before atomically publishing."""
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / wheel["filename"]
    if (
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_size <= zip_limits.MAX_MEMBER_BYTES
        and digest(zip_limits.read_file(path, limit=zip_limits.MAX_MEMBER_BYTES)) == wheel["sha256"]
    ):
        return path
    if offline:
        raise ValueError("Missing or corrupt cached wheel: " + wheel["filename"])
    with tempfile.TemporaryDirectory(prefix="wheel-", dir=cache) as directory:
        temporary = Path(directory) / wheel["filename"]
        _download(wheel["url"], temporary)
        if (
            digest(zip_limits.read_file(temporary, limit=zip_limits.MAX_MEMBER_BYTES))
            != wheel["sha256"]
        ):
            raise ValueError("Wheel SHA-256 mismatch: " + wheel["filename"])
        temporary.replace(path)
    return path


def license_destination(wheel, notice):
    filename = PurePosixPath(notice["path"]).name
    return f"licenses/dependencies/{wheel['package']}/{notice['sha256'][:12]}-{filename}"


def wheel_notices(wheel, raw):
    if len(raw) > zip_limits.MAX_MEMBER_BYTES:
        raise ValueError("Wheel size exceeds limit")
    if digest(raw) != wheel["sha256"]:
        raise ValueError("Wheel SHA-256 mismatch: " + wheel["filename"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        zip_limits.check_archive(archive)
        names = archive.namelist()
        for name in names:
            _safe_path(name)
        notices = {}
        for notice in wheel["licenses"]:
            content = zip_limits.read_member(
                archive, notice["path"], limit=zip_limits.MAX_NOTICE_BYTES
            )
            if not content or digest(content) != notice["sha256"]:
                raise ValueError("Wheel license notice mismatch")
            notices[license_destination(wheel, notice)] = content
        return notices


def prepare_source(source, destination, *, cache=None, offline=False):
    """Create one build-only source tree with the complete cross-platform bundle."""
    lock = json.loads((source / LOCK_NAME).read_text())
    manifest = tomllib.loads((source / "blender_manifest.toml").read_text())
    validate_lock(lock, manifest)
    cache = cache or source.parent / ".blender/wheels"
    if destination.exists():
        raise ValueError("Build source destination must be new")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Extension source must not contain symlinks")
    # Stage all verified bytes before creating the build input. A failed download
    # cannot produce a wheel-less or partially bundled extension.
    wheels = []
    notices = {}
    total = 0
    for wheel in lock["wheels"]:
        raw = zip_limits.read_file(
            cached_wheel(wheel, cache, offline=offline), limit=zip_limits.MAX_MEMBER_BYTES
        )
        total += len(raw)
        if total > zip_limits.MAX_TOTAL_BYTES:
            raise ValueError("Staged wheel size exceeds limit")
        notices.update(wheel_notices(wheel, raw))
        wheels.append((wheel["filename"], raw))
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "wheels"),
    )
    (destination / "wheels").mkdir()
    for filename, raw in wheels:
        (destination / "wheels" / filename).write_bytes(raw)
    for relative, content in notices.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return destination


def validate_bundle(candidate):
    """Validate a supplied ZIP against its own lock, never the checkout's version."""
    with zipfile.ZipFile(candidate) as archive:
        zip_limits.check_archive(archive)
        manifest = tomllib.loads(
            zip_limits.read_member(
                archive, "blender_manifest.toml", limit=zip_limits.MAX_METADATA_BYTES
            ).decode()
        )
        if LOCK_NAME not in archive.namelist() and not manifest.get("wheels"):
            return  # Historical extension without SDK dependencies.
        lock = json.loads(
            zip_limits.read_member(archive, LOCK_NAME, limit=zip_limits.MAX_METADATA_BYTES)
        )
        validate_lock(lock, manifest)
        actual = {
            name
            for name in archive.namelist()
            if name.startswith("wheels/") and not name.endswith("/")
        }
        expected = {"wheels/" + wheel["filename"] for wheel in lock["wheels"]}
        if actual != expected:
            raise ValueError("ZIP wheels differ from its SDK lock")
        for wheel in lock["wheels"]:
            for name, content in wheel_notices(
                wheel,
                zip_limits.read_member(
                    archive, "wheels/" + wheel["filename"], limit=zip_limits.MAX_MEMBER_BYTES
                ),
            ).items():
                if (
                    zip_limits.read_member(archive, name, limit=zip_limits.MAX_NOTICE_BYTES)
                    != content
                ):
                    raise ValueError("ZIP dependency license differs from its wheel")
