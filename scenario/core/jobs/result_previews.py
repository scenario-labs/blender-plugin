# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound previews of saved results and their private cache, without bpy.

Video, 3D and audio stills and short clips come from the SDK asset record's
``thumbnail`` and ``preview`` fields, downloaded through the existing signed
result transfer and its configured storage hosts. Images and audio waveforms
use the verified local result instead: this module issues a decode request that
holds a private verified copy. Blender decodes an image copy later on its main
thread; ``decode_envelope`` decodes an audio copy in an owned offline Blender
process. Every function here performs file or network I/O and belongs on the
dedicated preview worker lane, never in drawing or on Blender's main thread.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import struct
import tempfile
import time
import uuid
import zlib
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path

from ..audio_waveform import BINS, MAX_SECONDS, AudioEnvelope, WaveformCanceled, WaveformError
from . import audio_decode
from .local_render import RenderCancelled
from .media_probe import FORMATS, MediaProbeError, _snapshot
from .store import JobScope, StoredResult, _identity, _json
from .transfers import DownloadedResult, TransferError, _root

FORMAT = 1
STILL, CLIP, ENVELOPE = "still", "clip", "envelope"
RENDITIONS = (STILL, CLIP, ENVELOPE)
PREVIEW_EDGE = 256
# Server stills are decoded on Blender's main thread later: bound pixels, not
# only bytes, so a small compressed file cannot declare a huge decode.
STILL_MAX_EDGE = 4096
STILL_MAX_BYTES = 8 * 1024 * 1024
CLIP_MAX_BYTES = 64 * 1024 * 1024
DECODED_STILL_MAX_BYTES = 4 * 1024 * 1024
IMAGE_SOURCE_MAX_BYTES = 128 * 1024 * 1024
AUDIO_SOURCE_MAX_BYTES = 256 * 1024 * 1024
SIDECAR_MAX_BYTES = 128 * 1024
CACHE_MAX_BYTES = 512 * 1024 * 1024
WORK_STALE_SECONDS = 24 * 60 * 60
_HEX = re.compile(r"[0-9a-f]{64}")
_MEDIA_TYPE = re.compile(r"[a-z0-9][a-z0-9.+-]{0,63}/[a-z0-9][a-z0-9.+-]{0,63}")


class PreviewError(RuntimeError):
    """Sanitized preview failure; never a reason to download or generate again."""


class PreviewCanceled(PreviewError):
    """The preview lane task was canceled; partial work was discarded."""


class PreviewUnavailable(PreviewError):
    """A server preview transfer did not complete; poll again within the window.

    Covers every failure of the storage transfer itself, such as a redirect to
    another host, a connection error or an incomplete or oversized body. Bytes
    that arrive and then fail their receipt, format or dimension checks are a
    definitive ``PreviewError`` instead.
    """


class PreviewState(StrEnum):
    QUEUED = "queued"
    READY = "ready"
    PENDING = "pending"
    OFFLINE = "offline"
    MISSING = "missing"
    FAILED = "failed"
    DECODE = "decode"
    UNSUPPORTED = "unsupported"


def _png(head):
    return head.startswith(b"\x89PNG\r\n\x1a\n")


def _jpeg(head):
    return head.startswith(b"\xff\xd8\xff")


def _webp(head):
    return head[:4] == b"RIFF" and head[8:12] == b"WEBP"


def _exr(head):
    return head.startswith(b"\x76\x2f\x31\x01")


def _png_header(data):
    """Width, height, bit depth and color type from a PNG's checked IHDR chunk."""
    if len(data) < 33 or not _png(data) or data[8:16] != b"\x00\x00\x00\rIHDR":
        return None
    if zlib.crc32(data[12:29]) != struct.unpack(">I", data[29:33])[0]:
        return None
    return struct.unpack(">IIBB", data[16:26])


# Start-of-frame markers; DHT (C4), JPG (C8) and DAC (CC) share the range.
_JPEG_FRAMES = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}


def _jpeg_size(data):
    """Frame dimensions from the first JPEG start-of-frame segment."""
    index = 2
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            return None
        marker = data[index + 1]
        if marker == 0xFF:  # Fill byte before a marker.
            index += 1
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:  # Markers without a length.
            index += 2
            continue
        if marker in {0xD8, 0xD9, 0xDA}:  # No frame before the image or scan ended.
            return None
        length = int.from_bytes(data[index + 2 : index + 4], "big")
        if length < 2:
            return None
        if marker in _JPEG_FRAMES:
            if length < 8 or index + 9 > len(data):
                return None
            height = int.from_bytes(data[index + 5 : index + 7], "big")
            width = int.from_bytes(data[index + 7 : index + 9], "big")
            return width, height
        index += 2 + length
    return None


def _webp_size(data):
    """Canvas dimensions from a WebP VP8, VP8L or VP8X first chunk."""
    if len(data) < 30:
        return None
    chunk = data[12:16]
    if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        return (
            int.from_bytes(data[26:28], "little") & 0x3FFF,
            int.from_bytes(data[28:30], "little") & 0x3FFF,
        )
    if chunk == b"VP8L" and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8X":
        return (
            int.from_bytes(data[24:27], "little") + 1,
            int.from_bytes(data[27:30], "little") + 1,
        )
    return None


def still_size(data):
    """Declared pixel dimensions of a PNG, JPEG or WebP still, or None."""
    if _png(data):
        header = _png_header(data)
        return None if header is None else header[:2]
    if _jpeg(data):
        return _jpeg_size(data)
    if _webp(data):
        return _webp_size(data)
    return None


def _bounded_edges(width, height, limit=STILL_MAX_EDGE):
    return all(type(value) is int and 1 <= value <= limit for value in (width, height))


# ISO media brands for still images; a clip or audio container must not use them.
_IMAGE_BRANDS = {b"avif", b"avis", b"heic", b"heix", b"heim", b"heis", b"mif1", b"msf1"}


def _iso_media(head):
    return len(head) >= 12 and head[4:8] == b"ftyp" and head[8:12] not in _IMAGE_BRANDS


def _matroska(head):
    return head.startswith(b"\x1a\x45\xdf\xa3")


def _wav(head):
    return head[:4] == b"RIFF" and head[8:12] == b"WAVE"


def _mp3(head):
    return head.startswith(b"ID3") or (
        len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE6 == 0xE2
    )


def _aac(head):
    return head.startswith(b"ADIF") or (
        len(head) >= 2 and head[0] == 0xFF and head[1] & 0xF6 == 0xF0
    )


_AUDIO_CHECKS = {
    ".wav": _wav,
    ".mp3": _mp3,
    ".ogg": lambda head: head.startswith(b"OggS"),
    ".flac": lambda head: head.startswith(b"fLaC"),
    ".m4a": _iso_media,
    ".aac": _aac,
}
# Server stills and clips: formats Blender can decode, detected from content.
_SERVER = {
    STILL: {
        "image/png": (".png", _png),
        "image/jpeg": (".jpg", _jpeg),
        "image/webp": (".webp", _webp),
    },
    CLIP: {"video/mp4": (".mp4", _iso_media), "video/webm": (".webm", _matroska)},
}
_CAPS = {STILL: STILL_MAX_BYTES, CLIP: CLIP_MAX_BYTES}
# Saved results previewed from verified local bytes rather than a server image.
_LOCAL_IMAGES = {
    "image/png": (".png", _png),
    "image/jpeg": (".jpg", _jpeg),
    "image/jpg": (".jpg", _jpeg),
    "image/webp": (".webp", _webp),
    "image/exr": (".exr", _exr),
    "image/x-exr": (".exr", _exr),
}
_LOCAL_AUDIO = {
    media_type: (suffix, _AUDIO_CHECKS[suffix])
    for media_type, (kind, suffix, _) in FORMATS.items()
    if kind == "audio"
}
# Material libraries are text sidecars of an OBJ, not a previewable model.
_NO_SERVER_PREVIEW = frozenset({"model/mtl"})


def preview_kind(media_type):
    """Classify a saved result's MIME type; None means no preview is offered."""
    if not isinstance(media_type, str):
        return None
    if media_type in _LOCAL_IMAGES:
        return "image"
    if media_type in _LOCAL_AUDIO:
        return "audio"
    if media_type.startswith("video/"):
        return "video"
    if media_type in _NO_SERVER_PREVIEW:
        return None
    if media_type.startswith("model/") or media_type == "application/x-ply":
        return "3d"
    return None


def renditions(kind, *, clip=False):
    """Default renditions for a kind; server clips are only fetched on request."""
    if kind == "image":
        return (STILL,)
    if kind == "audio":
        return (STILL, ENVELOPE)
    if kind in {"video", "3d"}:
        return (STILL, CLIP) if clip else (STILL,)
    return ()


def is_local(kind, rendition):
    """Whether a rendition is decoded from the verified local result in Blender."""
    return (kind, rendition) in {("image", STILL), ("audio", ENVELOPE)}


def supports(kind, rendition):
    return rendition in renditions(kind, clip=True)


def scope_digest(scope):
    """The same scope partition as saved result files; never a credential."""
    if not isinstance(scope, JobScope):
        raise ValueError("A job scope is required")
    return hashlib.sha256(_json(asdict(scope)).encode()).hexdigest()


@dataclass(frozen=True)
class PreviewKey:
    """Exact binding of a preview to one saved asset receipt in one scope."""

    scope: str
    request: str
    asset_id: str
    media_type: str
    sha256: str
    size: int

    def __post_init__(self):
        _identity(self.asset_id)
        if (
            not all(isinstance(value, str) and _HEX.fullmatch(value) for value in self.digests)
            or not isinstance(self.media_type, str)
            or not _MEDIA_TYPE.fullmatch(self.media_type)
            or type(self.size) is not int
            or not 0 <= self.size <= 2**63 - 1
        ):
            raise ValueError("Use an exact saved-result preview identity")

    @property
    def digests(self):
        return self.scope, self.request, self.sha256

    @classmethod
    def for_result(cls, scope, request_id, result):
        if not isinstance(result, StoredResult) or result.receipt is None:
            raise ValueError("Preview only a downloaded result with a receipt")
        return cls(
            scope_digest(scope),
            hashlib.sha256(_identity(request_id).encode()).hexdigest(),
            result.asset.asset_id,
            result.asset.media_type,
            result.receipt.sha256,
            result.receipt.size,
        )

    @property
    def name(self):
        return hashlib.sha256(_json({"format": FORMAT, **asdict(self)}).encode()).hexdigest()


@dataclass(frozen=True)
class PreviewTarget:
    """One downloaded asset of a saved job, captured from the scoped store."""

    request_id: str
    asset_id: str
    media_type: str
    kind: str | None
    key: PreviewKey
    receipt: DownloadedResult = field(repr=False)


@dataclass(frozen=True)
class PreviewWork:
    """Renditions to resolve for one target in one lane batch."""

    target: PreviewTarget
    renditions: tuple[str, ...]
    final: bool = False
    force: bool = False

    def __post_init__(self):
        if (
            not isinstance(self.target, PreviewTarget)
            or not isinstance(self.renditions, tuple)
            or not self.renditions
            or len(set(self.renditions)) != len(self.renditions)
            or not set(self.renditions) <= set(RENDITIONS)
            or type(self.final) is not bool
            or type(self.force) is not bool
        ):
            raise ValueError("Use supported preview work for one saved result")


@dataclass(frozen=True)
class CachedPreview:
    """A verified cache entry; ``path`` stays inside the private preview cache."""

    rendition: str
    media_type: str | None = None
    path: Path | None = field(default=None, repr=False)
    size: int = 0
    sha256: str | None = None
    width: int | None = None
    height: int | None = None
    envelope: AudioEnvelope | None = field(default=None, repr=False)


@dataclass(frozen=True)
class MissingPreview:
    """The server offered no preview within the polling window; Retry clears it."""

    rendition: str


@dataclass(frozen=True, eq=False)
class DecodeRequest:
    """A private verified copy for local decoding, never the saved result.

    For a still, Blender writes a PNG fitting ``max_edge`` to ``output``. For an
    audio envelope, ``decode_envelope`` decodes ``source`` in an owned offline
    Blender process and caches the resulting ``AudioEnvelope``.
    """

    key: PreviewKey
    rendition: str
    media_type: str
    source: Path = field(repr=False)
    output: Path | None = field(repr=False)
    directory: Path = field(repr=False)
    max_edge: int = PREVIEW_EDGE
    max_seconds: int = MAX_SECONDS
    bins: int = BINS


@dataclass(frozen=True)
class RenditionOutcome:
    rendition: str
    state: PreviewState
    preview: CachedPreview | None = None
    request: DecodeRequest | None = field(default=None, repr=False)
    reason: str | None = None


@dataclass(frozen=True)
class PreviewOutcome:
    target: PreviewTarget
    renditions: tuple[RenditionOutcome, ...]


@dataclass(frozen=True)
class PreviewBatch:
    """Lane results for one scope; callers discard decode requests they do not use."""

    scope: JobScope
    outcomes: tuple[PreviewOutcome, ...]

    @property
    def requests(self):
        return tuple(
            item.request
            for outcome in self.outcomes
            for item in outcome.renditions
            if item.request is not None
        )


def _open_regular(path):
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    try:
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise
    try:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise PreviewError("Preview files must be regular local files")
    except BaseException:
        stream.close()
        raise
    return stream


def _digest(path, limit):
    """Stream one regular, nonsymlink file: size, SHA-256 and its first bytes."""
    with _open_regular(path) as stream:
        size, digest, head = 0, hashlib.sha256(), b""
        while chunk := stream.read(min(1024 * 1024, limit - size + 1)):
            if not head:
                head = chunk[:16]
            size += len(chunk)
            if size > limit:
                raise PreviewError("Preview file exceeds its size limit")
            digest.update(chunk)
    return size, digest.hexdigest(), head


def _read_small(path, limit):
    with _open_regular(path) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise PreviewError("Preview metadata exceeds its size limit")
    return data


def discard_directory(directory):
    """Remove one private preview work directory; leave anything else untouched."""
    directory = Path(directory)
    if not directory.name.startswith("preview-") or directory.parent.name != "work":
        return
    try:
        if stat.S_ISDIR(directory.lstat().st_mode):
            shutil.rmtree(directory, ignore_errors=True)
    except OSError:
        # Windows can refuse to remove an open file; the age sweep retries later.
        pass


class PreviewCache:
    """Private preview files below a caller-owned root, written by one lane per process.

    The root's parent must already exist under Blender's extension user
    directory. The cache is disposable: a root deleted while Blender runs is
    recreated as a private directory on the next lane command. Entries are
    partitioned by the job scope digest and keyed by the exact saved receipt,
    so another credential, project, request or byte content never shares them.
    Signed URLs are never written; only content digests and asset identities are.
    """

    def __init__(self, root):
        path = Path(root)
        if path.is_absolute():
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                pass  # The usual case: the root survives between lane commands.
            except OSError:
                raise PreviewError("Preview cache is unavailable") from None
        try:
            self._root = _root(path)
        except TransferError:
            raise PreviewError("Preview cache is unavailable") from None

    @property
    def root(self):
        return self._root

    def _directory(self, *parts, create):
        path = self._root
        for part in parts:
            path = path / part
            if create:
                try:
                    path.mkdir(mode=0o700)
                except FileExistsError:
                    pass  # Existing parts are checked to be directories just below.
            if not stat.S_ISDIR(path.lstat().st_mode):
                raise PreviewError("Preview cache entries must be private directories")
        return path

    def _entry(self, key, *, create=False):
        try:
            return self._directory("v1", key.scope, key.name, create=create)
        except FileNotFoundError:
            if create:
                raise PreviewError("Preview cache is unavailable") from None
            return None
        except OSError:
            raise PreviewError("Preview cache is unavailable") from None

    def read(self, key, rendition):
        """Return a verified entry, a missing marker, or None for a cache miss."""
        try:
            entry = self._entry(key)
        except PreviewError:
            return None
        if entry is None:
            return None
        sidecar = entry / f"{rendition}.json"
        try:
            value = json.loads(_read_small(sidecar, SIDECAR_MAX_BYTES))
            if (
                not isinstance(value, dict)
                or value.get("format") != FORMAT
                or value.get("key") != asdict(key)
                or value.get("rendition") != rendition
            ):
                return None
            if value.get("state") == "missing":
                return MissingPreview(rendition) if rendition in _SERVER else None
            if value.get("state") != "ready":
                return None
            if rendition == ENVELOPE:
                result = CachedPreview(
                    ENVELOPE, envelope=AudioEnvelope.from_dict(value["envelope"])
                )
            else:
                media_type = value["media_type"]
                suffix, check = _SERVER[rendition][media_type]
                path = entry / (rendition + suffix)
                size, digest, head = _digest(path, _CAPS[rendition])
                width, height = value.get("width"), value.get("height")
                if (
                    size != value["size"]
                    or digest != value["sha256"]
                    or not check(head)
                    or not (
                        _bounded_edges(width, height)
                        if rendition == STILL
                        else width is None and height is None
                    )
                ):
                    return None
                result = CachedPreview(rendition, media_type, path, size, digest, width, height)
        except (OSError, ValueError, KeyError, TypeError, RecursionError, PreviewError):
            # WaveformError is a ValueError: an invalid envelope is a cache miss.
            return None
        try:
            os.utime(sidecar)
        except OSError:
            pass  # Recency for eviction only: a failed touch still returns the entry.
        return result

    def _write_sidecar(self, entry, rendition, value):
        temporary = entry / f".{rendition}-{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("x", encoding="utf-8") as output:
                os.chmod(temporary, 0o600)
                output.write(json.dumps(value, sort_keys=True, allow_nan=False))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, entry / f"{rendition}.json")
        except BaseException:
            try:
                temporary.unlink()
            except OSError:
                pass  # Best effort: the original error matters; a stray .tmp file is ignored.
            raise

    def _sidecar(self, key, rendition, state, **values):
        return {
            "format": FORMAT,
            "key": asdict(key),
            "rendition": rendition,
            "state": state,
            **values,
        }

    def publish(self, key, rendition, staged, *, media_type, size, sha256, **details):
        """Link a validated staged file into its entry; never replace a valid entry.

        Stills record their checked pixel dimensions; clips record none.
        """
        width, height = details.get("width"), details.get("height")
        if not (
            _bounded_edges(width, height)
            if rendition == STILL
            else width is None and height is None
        ):
            raise PreviewError("Preview images need bounded pixel dimensions")
        existing = self.read(key, rendition)
        if isinstance(existing, CachedPreview):
            return existing
        suffix, _ = _SERVER[rendition][media_type]
        try:
            entry = self._entry(key, create=True)
            for other, _ in _SERVER[rendition].values():
                stale = entry / (rendition + other)
                if stale.is_symlink() or stale.exists():
                    stale.unlink()
            target = entry / (rendition + suffix)
            os.link(staged, target)
            os.chmod(target, 0o600)
            self._write_sidecar(
                entry,
                rendition,
                self._sidecar(
                    key,
                    rendition,
                    "ready",
                    media_type=media_type,
                    size=size,
                    sha256=sha256,
                    **details,
                ),
            )
        except OSError:
            raise PreviewError("Could not save the preview in the private cache") from None
        return CachedPreview(rendition, media_type, target, size, sha256, width, height)

    def publish_envelope(self, key, envelope):
        if not isinstance(envelope, AudioEnvelope):
            raise PreviewError("Provide a decoded audio envelope")
        existing = self.read(key, ENVELOPE)
        if isinstance(existing, CachedPreview):
            return existing
        try:
            entry = self._entry(key, create=True)
            self._write_sidecar(
                entry, ENVELOPE, self._sidecar(key, ENVELOPE, "ready", envelope=envelope.to_dict())
            )
        except (OSError, ValueError):
            raise PreviewError("Could not save the audio envelope in the private cache") from None
        return CachedPreview(ENVELOPE, envelope=envelope)

    def mark_missing(self, key, rendition):
        """Record that the polling window ended without a server preview."""
        if rendition not in _SERVER:
            raise ValueError("Only server previews can be missing")
        if isinstance(self.read(key, rendition), CachedPreview):
            return
        try:
            entry = self._entry(key, create=True)
            checked = int(time.time())
            self._write_sidecar(
                entry, rendition, self._sidecar(key, rendition, "missing", checked_at=checked)
            )
        except OSError:
            raise PreviewError("Could not save the preview state in the private cache") from None

    def forget(self, key, rendition):
        """Clear a missing marker before an explicit retry; keep verified entries."""
        if isinstance(self.read(key, rendition), MissingPreview):
            try:
                (self._entry(key) / f"{rendition}.json").unlink()
            except (OSError, TypeError):
                pass  # Already gone, or the entry vanished: the retry polls either way.

    def workspace(self):
        """A new private work directory on the cache filesystem for staging.

        Only its name comes from ``mkdtemp``. Python 3.12 and later return that
        path through ``abspath``, so the canonical root's spelling, which is the
        extended namespace on Windows, is kept for ``discard`` and decode checks.
        """
        try:
            work = self._directory("work", create=True)
            return work / Path(tempfile.mkdtemp(prefix="preview-", dir=work)).name
        except OSError:
            raise PreviewError("Preview cache is unavailable") from None

    def discard(self, directory):
        directory = Path(directory)
        if directory.parent == self._root / "work":
            discard_directory(directory)

    def sweep(self, *, now=None, older_than=WORK_STALE_SECONDS):
        """Remove abandoned work directories, for example after a crash."""
        now = time.time() if now is None else now
        try:
            children = tuple((self._root / "work").iterdir())
        except OSError:
            return
        for child in children:
            try:
                info = child.lstat()
            except OSError:
                continue
            if (
                child.name.startswith("preview-")
                and stat.S_ISDIR(info.st_mode)
                and now - info.st_mtime > older_than
            ):
                discard_directory(child)

    def evict(self, *, max_bytes=CACHE_MAX_BYTES, now=None, keep_seconds=60):
        """Remove least recently used entries beyond the byte budget.

        Only bytes actually removed count as freed: an entry the system keeps,
        such as a file Windows holds open, leaves the next oldest entry in line
        and is tried again on the next pass.
        """
        now = time.time() if now is None else now
        entries, total = [], 0
        try:
            scopes = tuple((self._root / "v1").iterdir())
        except OSError:
            return
        for scope in scopes:
            try:
                if not _HEX.fullmatch(scope.name) or not stat.S_ISDIR(scope.lstat().st_mode):
                    continue
                names = tuple(scope.iterdir())
            except OSError:
                continue
            for entry in names:
                try:
                    if not _HEX.fullmatch(entry.name) or not stat.S_ISDIR(entry.lstat().st_mode):
                        continue
                    files = [item.lstat() for item in entry.iterdir()]
                except OSError:
                    continue
                size = sum(item.st_size for item in files if stat.S_ISREG(item.st_mode))
                recent = max((item.st_mtime for item in files), default=0.0)
                entries.append((recent, size, entry))
                total += size
        for recent, size, entry in sorted(entries, key=lambda item: item[0]):
            if total <= max_bytes or now - recent < keep_seconds:
                break
            shutil.rmtree(entry, ignore_errors=True)
            total -= size - _remaining_bytes(entry, size)


def _remaining_bytes(entry, size):
    """Regular-file bytes still in one cache entry; all of them if unreadable."""
    try:
        files = [item.lstat() for item in entry.iterdir()]
    except FileNotFoundError:
        if not os.path.lexists(entry):
            return 0
        return size
    except OSError:
        return size
    return sum(item.st_size for item in files if stat.S_ISREG(item.st_mode))


def server_sources(record, target):
    """Signed preview URLs from one SDK asset record; URLs stay in memory only."""
    if (
        not isinstance(record, dict)
        or record.get("id") != target.asset_id
        or record.get("mimeType") != target.media_type
    ):
        raise PreviewError("Scenario returned different metadata for this saved result")
    sources = {}
    for rendition, name in ((STILL, "thumbnail"), (CLIP, "preview")):
        value = record.get(name)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise PreviewError("Scenario returned invalid preview metadata")
        url = value.get("url")
        if url is None or url == "":
            continue
        try:
            if not isinstance(url, str):
                raise ValueError
            sources[rendition] = (_identity(value.get("assetId")), url)
        except ValueError:
            raise PreviewError("Scenario returned invalid preview metadata") from None
    return sources


def fetch(cache, downloader, target, rendition, source, cancel=None):
    """Download one server still or clip with the bounded result transfer, then cache it.

    ``cancel`` stops the transfer at its next permission check, so retirement
    does not wait for a whole clip. A transfer that does not complete raises
    ``PreviewUnavailable`` so the caller can poll again; the downloader's
    one-attempt and same-host redirect policy is unchanged. A still must
    declare at most ``STILL_MAX_EDGE`` pixels per side before it is cached.
    """
    source_asset_id, url = source
    directory = cache.workspace()
    try:
        try:
            receipt = downloader.download(
                url, root=directory, name="preview.bin", max_bytes=_CAPS[rendition], cancel=cancel
            )
        except TransferError:
            if cancel is not None and cancel.is_set():
                raise PreviewCanceled("Preview preparation was canceled") from None
            raise PreviewUnavailable("The preview download did not complete") from None
        path = downloader.verify(directory, receipt)
        with _open_regular(path) as stream:
            head = stream.read(16)
        media_type = next(
            (name for name, (_, check) in _SERVER[rendition].items() if check(head)), None
        )
        if media_type is None:
            raise PreviewError("Scenario returned a preview in an unsupported format")
        details = {}
        if rendition == STILL:
            size = still_size(_read_small(path, STILL_MAX_BYTES))
            if size is None or 0 in size:
                raise PreviewError("Scenario returned a preview image without valid dimensions")
            if not _bounded_edges(*size):
                raise PreviewError(
                    f"Scenario returned a preview image larger than {STILL_MAX_EDGE} pixels"
                )
            details = {"width": size[0], "height": size[1]}
        return cache.publish(
            target.key,
            rendition,
            path,
            media_type=media_type,
            size=receipt.size,
            sha256=receipt.sha256,
            source_asset_id=source_asset_id,
            **details,
        )
    except TransferError:
        # Only verification raises here: the staged bytes no longer match the
        # receipt the transfer just returned, which another poll cannot repair.
        raise PreviewError("The downloaded preview does not match its receipt; use Retry") from None
    except OSError:
        raise PreviewError("The preview download could not be checked") from None
    finally:
        cache.discard(directory)


def prepare_decode(cache, target, rendition, source, cancel):
    """Copy one saved result, rehashing it against its receipt, for Blender decoding."""
    if (target.kind, rendition) == ("image", STILL):
        suffix, check = _LOCAL_IMAGES[target.media_type]
        limit = IMAGE_SOURCE_MAX_BYTES
    elif (target.kind, rendition) == ("audio", ENVELOPE):
        suffix, check = _LOCAL_AUDIO[target.media_type]
        limit = AUDIO_SOURCE_MAX_BYTES
    else:
        raise PreviewError("This saved result has no local preview")
    if not 0 < target.receipt.size <= limit:
        raise PreviewError("The saved result is too large to preview")
    directory = cache.workspace()
    try:
        copy = directory / ("source" + suffix)
        _snapshot(Path(source), target.receipt, copy, cancel)
        os.chmod(copy, 0o600)
        with _open_regular(copy) as stream:
            head = stream.read(16)
        if not check(head):
            raise PreviewError("The saved result contents do not match its type")
        return DecodeRequest(
            target.key,
            rendition,
            target.media_type,
            copy,
            directory / "preview.png" if rendition == STILL else None,
            directory,
        )
    except RenderCancelled:
        cache.discard(directory)
        raise PreviewCanceled("Preview preparation was canceled") from None
    except PreviewError:
        cache.discard(directory)
        raise
    except (OSError, ValueError, MediaProbeError, TransferError):
        cache.discard(directory)
        raise PreviewError("The saved result no longer matches its receipt") from None
    except BaseException:
        cache.discard(directory)
        raise


def _decoded_png(path, max_edge):
    """Check a Blender-written PNG's signature, header and bounds before caching it."""
    data = _read_small(path, DECODED_STILL_MAX_BYTES)
    if len(data) < 33 or not _png(data) or data[8:16] != b"\x00\x00\x00\rIHDR":
        raise PreviewError("Decoded preview is not a PNG image")
    header = _png_header(data)
    if (
        header is None
        or not _bounded_edges(*header[:2], limit=max_edge)
        or header[2] not in {8, 16}
        or header[3] not in {0, 2, 3, 4, 6}
    ):
        raise PreviewError("Decoded preview exceeds its size limit or is malformed")
    width, height = header[:2]
    return width, height, len(data), hashlib.sha256(data).hexdigest()


def _owned(cache, request):
    return (
        isinstance(request, DecodeRequest)
        and request.directory.parent == cache.root / "work"
        and request.source.parent == request.directory
        and (request.output is None or request.output.parent == request.directory)
    )


def finish_decode(cache, request, *, envelope=None):
    """Validate Blender's decoded output and cache it; always discard the private copy."""
    if not _owned(cache, request):
        raise PreviewError("Use a decode request issued by this preview cache")
    try:
        if request.rendition == STILL:
            if envelope is not None:
                raise PreviewError("A still preview takes no audio envelope")
            try:
                width, height, size, digest = _decoded_png(request.output, request.max_edge)
            except OSError:
                raise PreviewError("Blender did not write the decoded preview") from None
            return cache.publish(
                request.key,
                STILL,
                request.output,
                media_type="image/png",
                size=size,
                sha256=digest,
                width=width,
                height=height,
            )
        if not isinstance(envelope, AudioEnvelope) or len(envelope.rms) > request.bins:
            raise PreviewError("Provide the bounded decoded audio envelope")
        return cache.publish_envelope(request.key, envelope)
    finally:
        cache.discard(request.directory)


def decode_envelope(cache, request, spec, cancel):
    """Decode an audio request's private copy in an owned offline Blender, then cache it.

    The child reads only the receipt-checked copy and is terminated on
    cancellation or timeout. The copy is removed on every exit; a failure
    caches nothing and keeps its sanitized reason for the caller.
    """
    if not _owned(cache, request) or request.rendition != ENVELOPE:
        raise PreviewError("Use an audio decode request issued by this preview cache")
    try:
        try:
            envelope = audio_decode.decode(
                request.source,
                request.directory,
                spec,
                cancel=cancel,
                max_seconds=request.max_seconds,
                bins=request.bins,
            )
        except WaveformCanceled:
            raise PreviewCanceled("Preview preparation was canceled") from None
        except WaveformError as error:
            raise PreviewError(str(error)) from None
        return finish_decode(cache, request, envelope=envelope)
    finally:
        cache.discard(request.directory)
