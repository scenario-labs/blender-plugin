# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Owned offline Film case-study bundles, without bpy, service calls or a shared worker.

The parent writes a private snapshot of the chosen Film scenes on Blender's main
thread. This module copies the stamped external media into private staging, has an
offline Blender child rewrite that snapshot into a portable data library whose
media references are bundle-relative and whose Scenario private properties are
removed, reopens the library in a second child to verify its references, scans it
for the caller's private identifiers, adds the sanitized documents and packs one
ZIP archive. ``local_export.publish`` saves the archive without overwriting.
Nothing here contacts Scenario, spends credits or writes a job record. The bundle
layout adapts Emmanuel de Maistre's Scenario Studio case-study export.
"""

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from ..scene.film_case_study import (
    GUIDE_FILE,
    LEDGER_FILE,
    MANIFEST_FILE,
    MEDIA_FOLDER,
    RECIPE_FILE,
    encode,
)
from .local_export import (
    _RESERVED_CHARACTERS,
    MAX_MEDIA,
    MAX_MEDIA_BYTES,
    MAX_TIMEOUT,
    SPACE_MARGIN,
    ExportMedia,
    LocalExportError,
    MediaReceipt,
    StagedFile,
    _child,
    _same,
    check_unused,
    portable_name,
)
from .local_render import LocalRenderError, RenderCancelled, _environment, blender_path, digest
from .transfers import TransferError

MAX_SCENES = 256
MAX_BLEND_BYTES = 4 * 1024**3
MAX_DOCUMENT_BYTES = 16 * 1024**2
MAX_REPORT_BYTES = 4 * 1024**2
MAX_MARKERS = 4096
MAX_ARCHIVE_BYTES = MAX_MEDIA_BYTES + MAX_BLEND_BYTES + 4 * MAX_DOCUMENT_BYTES + 64 * 1024**2
KINDS = frozenset({"movie", "sound", "image", "font"})
DOCUMENTS = (RECIPE_FILE, LEDGER_FILE, MANIFEST_FILE, GUIDE_FILE)
STAGING_PREFIX = "film-export-case-study-"
BUNDLE = "bundle"
SNAPSHOT = "snapshot.blend"
ARCHIVE = "case-study.zip"
_PRIVATE_FOUND = (
    "The case-study files still hold a private Scenario identifier or local folder;"
    " nothing was saved"
)


def _portable_stem(title):
    """The title with control and reserved characters replaced, or ``Film``."""
    text = "".join(
        "-" if ord(c) < 32 or ord(c) == 127 or c in _RESERVED_CHARACTERS else c for c in str(title)
    )
    return " ".join(text.split()).strip(" .")


def bundle_names(title):
    """Return the archive's top folder, its .blend name and a suggested ZIP name.

    Every name stays portable, including on Windows, and within 255 bytes.
    """
    stem = _portable_stem(title)
    suffixes = (" Case Study", " Case Study.blend", " - Case Study.zip")
    while stem and max(len((stem + suffix).encode("utf-8")) for suffix in suffixes) > 255:
        stem = stem[:-1].rstrip(" .")
    names = tuple((stem or "Film") + suffix for suffix in suffixes)
    if not all(portable_name(name) for name in names):
        names = tuple("Film" + suffix for suffix in suffixes)
    return names


def media_name(index, kind, path):
    """A neutral portable name: ``001 movie.mp4``; the original name is not kept."""
    if kind not in KINDS or type(index) is not int or index < 1:
        raise ValueError("Use a supported case-study media kind")
    suffix = Path(str(path)).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ""
    return f"{index:03d} {kind}{suffix}"


@dataclass(frozen=True)
class BundleMedia:
    """One stamped external file and its neutral name inside the bundle's Media folder."""

    stamp: ExportMedia
    name: str
    kind: str

    def __post_init__(self):
        if not isinstance(self.stamp, ExportMedia):
            raise ValueError("Use a stamped case-study media file")
        if self.kind not in KINDS:
            raise ValueError("Use a supported case-study media kind")
        if not portable_name(self.name) or self.name.startswith("."):
            raise ValueError("Use portable case-study media names")


def _document_text(name, text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ValueError("Keep each case-study document within 16 MiB")
    if name != GUIDE_FILE:
        try:
            value = json.loads(text)
        except ValueError:
            raise ValueError("Case-study documents must be JSON") from None
        if not isinstance(value, dict):
            raise ValueError("Case-study documents must be JSON objects")


@dataclass(frozen=True, eq=False)
class CaseStudySpec:
    """An approved private snapshot, its stamped media and the sanitized documents."""

    directory: Path
    binary: Path
    worker: Path
    snapshot_sha256: str
    top: str
    blend: str
    scenes: tuple[str, ...]
    media: tuple[BundleMedia, ...]
    documents: tuple[tuple[str, str], ...] = field(repr=False)
    markers: tuple[str, ...] = field(default=(), repr=False)
    timeout: float | None = None

    def __post_init__(self):
        if any(
            not isinstance(p, Path) or not p.is_absolute()
            for p in (self.directory, self.binary, self.worker)
        ):
            raise ValueError("Use absolute owned case-study paths")
        if (
            not isinstance(self.snapshot_sha256, str)
            or len(self.snapshot_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.snapshot_sha256)
        ):
            raise ValueError("Bind the exact scene snapshot")
        if (
            not portable_name(self.top)
            or not portable_name(self.blend)
            or not self.blend.endswith(".blend")
            or self.top.startswith(".")
            or self.blend.startswith(".")
        ):
            raise ValueError("Use portable case-study bundle names")
        if (
            not isinstance(self.scenes, tuple)
            or not 1 <= len(self.scenes) <= MAX_SCENES
            or any(
                not isinstance(name, str) or not name or "\0" in name or len(name) > 1024
                for name in self.scenes
            )
            or len(set(self.scenes)) != len(self.scenes)
        ):
            raise ValueError("Bundle between one and 256 distinct named scenes")
        if (
            not isinstance(self.media, tuple)
            or len(self.media) > MAX_MEDIA
            or any(not isinstance(item, BundleMedia) for item in self.media)
            or len({item.stamp.path for item in self.media}) != len(self.media)
            or len({item.name.casefold() for item in self.media}) != len(self.media)
            or self.media_bytes > MAX_MEDIA_BYTES
        ):
            raise ValueError("Bundle at most 2,000 distinct media files totalling 16 GiB")
        if (
            not isinstance(self.documents, tuple)
            or any(not isinstance(item, tuple) or len(item) != 2 for item in self.documents)
            or tuple(name for name, _ in self.documents) != DOCUMENTS
        ):
            raise ValueError("Provide the sanitized recipe, ledger, manifest and guide")
        for name, text in self.documents:
            _document_text(name, text)
        if (
            not isinstance(self.markers, tuple)
            or len(self.markers) > MAX_MARKERS
            or any(
                not isinstance(value, str)
                or not 6 <= len(value) <= 256
                or any(ord(c) < 32 or ord(c) == 127 for c in value)
                for value in self.markers
            )
        ):
            raise ValueError("Use bounded private identifiers for the case-study scan")
        if self.timeout is not None and (
            isinstance(self.timeout, bool)
            or not isinstance(self.timeout, (int, float))
            or not math.isfinite(self.timeout)
            or not 0 < self.timeout <= MAX_TIMEOUT
        ):
            raise ValueError("Use a finite positive case-study timeout of at most six hours")

    @property
    def media_bytes(self):
        return sum(item.stamp.size for item in self.media)

    @property
    def child_timeout(self):
        """Explicit timeout, else ten minutes plus a margin per media file and scene."""
        if self.timeout is not None:
            return self.timeout
        return min(MAX_TIMEOUT, 600 + 2 * len(self.media) + 5 * len(self.scenes))

    @property
    def root(self):
        return self.directory / BUNDLE

    def parameters(self):
        """The child's bundle parameters; media keys are the snapshot's absolute paths."""
        return {
            "mode": "bundle",
            "scenes": list(self.scenes),
            "media": [
                {"path": str(item.stamp.path), "name": item.name, "kind": item.kind}
                for item in self.media
            ],
            "output": blender_path(self.root / self.blend),
            "report": blender_path(self.directory / "bundle.json"),
        }


@dataclass(frozen=True)
class PublishedBundle:
    destination: Path
    sha256: str
    size: int
    scenes: tuple[str, ...]
    blend_sha256: str
    media: tuple[MediaReceipt, ...] = field(repr=False)


@dataclass(frozen=True, eq=False)
class StagedBundle(StagedFile):
    """A verified private archive that the caller may publish again without rebuilding."""

    noun: ClassVar[str] = "case-study archive"
    kind: ClassVar[str] = "case-study"
    directory: Path = field(repr=False)
    path: Path = field(repr=False)
    sha256: str
    size: int
    scenes: tuple[str, ...]
    blend_sha256: str
    media: tuple[MediaReceipt, ...] = field(repr=False)

    def published(self, destination):
        return PublishedBundle(
            destination, self.sha256, self.size, self.scenes, self.blend_sha256, self.media
        )


def estimated_bytes(spec):
    """Conservative staging need: media copies, the archive and four times the snapshot."""
    try:
        snapshot = os.stat(spec.root / SNAPSHOT).st_size
    except OSError:
        snapshot = 0
    return 2 * spec.media_bytes + 8 * snapshot + SPACE_MARGIN, (
        spec.media_bytes + 4 * snapshot + SPACE_MARGIN
    )


def check_space(spec, destination):
    """Fail early on an obviously full disk; a full disk later still fails cleanly."""
    staging, target = estimated_bytes(spec)
    folder = Path(destination).parent
    if not folder.is_dir():
        raise LocalExportError("The destination folder must already exist")
    try:
        same = os.stat(spec.directory).st_dev == os.stat(folder).st_dev
        enough = (
            shutil.disk_usage(spec.directory).free >= staging + (target if same else 0)
            and shutil.disk_usage(folder).free >= target
        )
    except OSError:
        enough = False
    if not enough:
        raise LocalExportError("Not enough free disk space for this case-study export")


def _copy_media(spec, target, cancel, progress):
    """Copy every stamped file into private staging, hashing; stamps must not change."""
    target.mkdir(mode=0o700)
    total, done, receipts = spec.media_bytes, 0, []
    # NONBLOCK keeps a substituted FIFO from hanging before the identity check.
    reading = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    writing = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    writing |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    progress("media", 0, total)
    for item in spec.media:
        value, copied = hashlib.sha256(), 0
        try:
            with os.fdopen(os.open(item.stamp.path, reading), "rb") as source:
                if not _same(item.stamp, os.fstat(source.fileno())):
                    raise LocalExportError("Case-study media changed after the scene snapshot")
                with os.fdopen(os.open(target / item.name, writing, 0o600), "wb") as copy:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        if cancel.is_set():
                            raise RenderCancelled("Film case-study export cancelled")
                        copied += len(chunk)
                        if copied > item.stamp.size:
                            break
                        value.update(chunk)
                        copy.write(chunk)
                        done += len(chunk)
                        progress("media", min(done, total), total)
                if copied != item.stamp.size or not _same(item.stamp, os.fstat(source.fileno())):
                    raise LocalExportError("Case-study media changed while copying")
        except OSError:
            raise LocalExportError("Case-study media is unavailable") from None
        receipts.append(MediaReceipt(item.name, item.stamp.size, value.hexdigest()))
    return tuple(receipts)


def _read_report(path, message):
    """Read one bounded JSON child report; a missing or odd file fails without its path."""
    try:
        if path.is_symlink() or not 0 < path.stat().st_size <= MAX_REPORT_BYTES:
            raise LocalExportError(message)
        value = json.loads(path.read_bytes())
    except (OSError, ValueError, RecursionError):
        raise LocalExportError(message) from None
    if not isinstance(value, dict):
        raise LocalExportError(message)
    return value


def check_bundle(spec, report):
    """Require the child to have written exactly the approved scenes."""
    written = report.get("written")
    if (
        not isinstance(written, list)
        or len(written) != len(spec.scenes)
        or set(written) != set(spec.scenes)
    ):
        raise LocalExportError("The case-study library does not hold the approved scenes")


def _portable(value):
    return value.replace("\\", "/") if isinstance(value, str) else value


def check_verified(spec, report):
    """Check what a fresh Blender saw in the written library: scenes, paths and data."""
    expected = {MEDIA_FOLDER + "/" + item.name for item in spec.media}
    try:
        scenes = report["scenes"]
        paths = [_portable(value) for value in report["paths"]]
        packed = [_portable(value) for value in report["packed_paths"]]
        valid = (
            isinstance(scenes, list)
            and set(scenes) == set(spec.scenes)
            and len(scenes) == len(spec.scenes)
            and report["libraries"] == 0
            and report["properties"] == []
            and report["missing"] == []
            and all(isinstance(value, str) for value in (*paths, *packed))
            and {value[2:] for value in paths if value.startswith("//")} == expected
            and all(value.startswith("//") and value[2:] in expected for value in paths)
            and all(value.startswith("//Packed/") for value in packed)
        )
    except (KeyError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise LocalExportError(
            "The case-study library still references files outside the bundle or private"
            " properties; inspect its retained log"
        )


def _scan(path, markers, cancel, progress):
    """Refuse a library that still contains any caller-supplied private identifier."""
    values = sorted({value.encode("utf-8") for value in markers}, key=len, reverse=True)
    if not values:
        return
    pattern = re.compile(b"|".join(re.escape(value) for value in values))
    overlap, tail = len(values[0]) - 1, b""
    with path.open("rb") as stream:
        total, done = os.fstat(stream.fileno()).st_size, 0
        progress("scan", 0, total)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            if cancel.is_set():
                raise RenderCancelled("Film case-study export cancelled")
            window = tail + chunk
            if pattern.search(window):
                raise LocalExportError(_PRIVATE_FOUND)
            tail = window[-overlap:] if overlap else b""
            done += len(chunk)
            progress("scan", min(done, total), total)


def _documents(spec, receipts, blend, report):
    """Complete the manifest with file receipts; check every document for markers."""
    documents = dict(spec.documents)
    manifest = json.loads(documents[MANIFEST_FILE])
    manifest["blend_file"] = {"file": spec.blend, "size": blend[0], "sha256": blend[1]}
    kinds = {item.name: item.kind for item in spec.media}
    manifest["media"] = [
        {
            "file": MEDIA_FOLDER + "/" + receipt.name,
            "kind": kinds[receipt.name],
            "size": receipt.size,
            "sha256": receipt.sha256,
        }
        for receipt in receipts
    ]
    counts = report.get("counts", {})
    manifest["media_storage"] = {
        "mode": "external_relative_media_with_packed_data",
        "media_bytes": sum(receipt.size for receipt in receipts),
        **{
            key: counts[key]
            for key in (
                "recreated_sound_strips",
                "repacked_images",
                "packed_fonts",
                "packed_sounds",
            )
            if type(counts.get(key)) is int
        },
    }
    documents[MANIFEST_FILE] = encode(manifest)
    for name, text in documents.items():
        _document_text(name, text)
        lowered = text.casefold()
        if any(marker.casefold() in lowered for marker in spec.markers):
            raise LocalExportError(_PRIVATE_FOUND)
    return {name: text.encode("utf-8") for name, text in documents.items()}


def _date_time():
    year, month, day, hour, minute, second = time.localtime()[:6]
    return (max(1980, year), month, day, hour, minute, second)


def _members(spec, root, documents, blend, receipts):
    """Archive members in order: name, source, size, digest and compression."""
    top = spec.top + "/"
    members = [(top + spec.blend, root / spec.blend, blend[0], blend[1], zipfile.ZIP_DEFLATED)]
    for name in DOCUMENTS:
        data = documents[name]
        members.append(
            (
                top + name,
                root / name,
                len(data),
                hashlib.sha256(data).hexdigest(),
                zipfile.ZIP_DEFLATED,
            )
        )
    for receipt in receipts:
        members.append(
            (
                top + MEDIA_FOLDER + "/" + receipt.name,
                root / MEDIA_FOLDER / receipt.name,
                receipt.size,
                receipt.sha256,
                # Movies and sounds are already compressed; store them as they are.
                zipfile.ZIP_STORED,
            )
        )
    return members


def _archive(path, members, cancel, progress):
    total, done, stamp = sum(item[2] for item in members), 0, _date_time()
    progress("archive", 0, total)
    with zipfile.ZipFile(path, "x", allowZip64=True) as archive:
        for name, source, size, sha256, method in members:
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.compress_type, info.external_attr, info.file_size = method, 0o644 << 16, size
            value, written = hashlib.sha256(), 0
            with source.open("rb") as stream, archive.open(info, "w") as target:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    if cancel.is_set():
                        raise RenderCancelled("Film case-study export cancelled")
                    value.update(chunk)
                    written += len(chunk)
                    if written > size:
                        break
                    target.write(chunk)
                    done += len(chunk)
                    progress("archive", min(done, total), total)
            if (written, value.hexdigest()) != (size, sha256):
                raise LocalExportError("A case-study file changed while archiving")


def check_archive(path, members, cancel, progress):
    """Reread every member: exact names, order, sizes, CRCs and content hashes."""
    total, done = sum(item[2] for item in members), 0
    progress("check", 0, total)
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if [info.filename for info in infos] != [item[0] for item in members]:
                raise LocalExportError("The case-study archive has unexpected entries")
            for info, (_, _, size, sha256, method) in zip(infos, members, strict=True):
                if info.file_size != size or info.compress_type != method or info.is_dir():
                    raise LocalExportError("The case-study archive has unexpected entries")
                value = hashlib.sha256()
                with archive.open(info) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        if cancel.is_set():
                            raise RenderCancelled("Film case-study export cancelled")
                        value.update(chunk)
                        done += len(chunk)
                        progress("check", min(done, total), total)
                if value.hexdigest() != sha256:
                    raise LocalExportError("The case-study archive does not match its files")
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError):
        raise LocalExportError("The case-study archive is not a complete ZIP file") from None


def build(spec, *, cancel=None, progress=None):
    """Build, verify and archive an owned snapshot; keep staging, logs and reports.

    The snapshot is consumed once. The archive holds the rewritten library, the
    sanitized documents and the media copies under one top folder. File system
    errors never expose private staging paths.
    """
    if not isinstance(spec, CaseStudySpec):
        raise TypeError("Use an approved Film case-study specification")
    cancel = cancel if cancel is not None else threading.Event()
    progress = progress if progress is not None else (lambda *_: None)
    try:
        return _build(spec, cancel, progress)
    except OSError:
        raise LocalExportError(
            "Film case-study export could not use its private staging files; prepare it again"
        ) from None


def _blender(spec, blend, parameters, log, env, cancel):
    _child(
        [
            blender_path(spec.binary),
            "--quiet",
            "--offline-mode",
            "--factory-startup",
            "--disable-autoexec",
            "--background",
            blender_path(blend),
            "--python-exit-code",
            "1",
            "--python",
            blender_path(spec.worker),
            "--",
            blender_path(parameters),
        ],
        log=log,
        env=env,
        timeout=spec.child_timeout,
        cancel=cancel,
    )


def _build(spec, cancel, progress):
    root, directory = spec.root, spec.directory
    snapshot, output = root / SNAPSHOT, root / spec.blend
    started, verify = directory / "started.json", directory / "verify.json"
    archive = directory / "output" / ARCHIVE
    # Validate every child-visible path before consuming this export's admission.
    for path in (snapshot, output, spec.binary, spec.worker, started, verify):
        blender_path(path)
    for item in spec.media:
        blender_path(root / MEDIA_FOLDER / item.name)
    if any(path.is_symlink() or not path.is_dir() for path in (directory, root)):
        raise LocalExportError("The owned case-study directory is unavailable")
    check_unused(spec)
    try:
        current = digest(snapshot)
    except (OSError, LocalRenderError, TransferError):
        current = None
    if current != spec.snapshot_sha256:
        raise LocalExportError("The case-study scene snapshot changed")
    if not spec.binary.is_file() or not spec.worker.is_file():
        raise LocalExportError("The Blender executable or bundled case-study worker is unavailable")
    if cancel.is_set():
        raise RenderCancelled("Film case-study export cancelled")
    with started.open("x", encoding="utf-8") as stream:
        json.dump(spec.parameters(), stream)
    receipts = _copy_media(spec, root / MEDIA_FOLDER, cancel, progress)
    with tempfile.TemporaryDirectory(prefix="worker-", dir=directory) as owned:
        profile, temporary = Path(owned) / "profile", Path(owned) / "tmp"
        profile.mkdir()
        temporary.mkdir()
        env = _environment(profile, temporary)
        progress("bundle", 0, 1)
        _blender(spec, snapshot, started, directory / "bundle.log", env, cancel)
        report = _read_report(directory / "bundle.json", "The case-study library report is missing")
        check_bundle(spec, report)
        if output.is_symlink() or not output.is_file():
            raise LocalExportError("The case-study library was not written")
        if not 0 < output.stat().st_size <= MAX_BLEND_BYTES:
            raise LocalExportError("The case-study library exceeded the size policy")
        progress("bundle", 1, 1)
        progress("verify", 0, 1)
        with verify.open("x", encoding="utf-8") as stream:
            json.dump(
                {
                    "mode": "verify",
                    "scenes": list(spec.scenes),
                    "media": [{"name": item.name, "kind": item.kind} for item in spec.media],
                    "report": blender_path(directory / "verified.json"),
                },
                stream,
            )
        _blender(spec, output, verify, directory / "verify.log", env, cancel)
        check_verified(
            spec,
            _read_report(
                directory / "verified.json", "The case-study verification report is missing"
            ),
        )
        progress("verify", 1, 1)
    _scan(output, spec.markers, cancel, progress)
    try:
        blend = (output.stat().st_size, digest(output, maximum=MAX_BLEND_BYTES, cancel=cancel))
    except RenderCancelled:
        raise RenderCancelled("Film case-study export cancelled") from None
    except (LocalRenderError, TransferError):
        raise LocalExportError("The case-study library exceeded the size policy") from None
    documents = _documents(spec, receipts, blend, report)
    writing = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    writing |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    for name, data in documents.items():
        with os.fdopen(os.open(root / name, writing, 0o600), "wb") as stream:
            stream.write(data)
    members = _members(spec, root, documents, blend, receipts)
    archive.parent.mkdir(mode=0o700)
    _archive(archive, members, cancel, progress)
    size = archive.stat().st_size
    if not 0 < size <= MAX_ARCHIVE_BYTES:
        raise LocalExportError("The case-study archive exceeded the size policy")
    check_archive(archive, members, cancel, progress)
    try:
        sha256 = digest(archive, maximum=MAX_ARCHIVE_BYTES, cancel=cancel)
    except RenderCancelled:
        raise RenderCancelled(
            "Film case-study export cancelled; staged files are retained"
        ) from None
    # The verified archive holds the copies; the staged originals are no longer needed.
    shutil.rmtree(root / MEDIA_FOLDER, ignore_errors=True)
    if cancel.is_set():
        raise RenderCancelled("Film case-study export cancelled; staged files are retained")
    return StagedBundle(directory, archive, sha256, size, spec.scenes, blend[1], receipts)
