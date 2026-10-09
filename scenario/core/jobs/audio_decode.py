# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Audio waveform envelopes decoded in an owned offline Blender process, without bpy.

Blender's audio module holds Python's global interpreter lock for a whole
decode: on Blender 5.0.1, 5.1.2 and 5.2.1, ten minutes of compressed stereo
audio decoded on a worker thread paused the main thread for 0.4 to 0.55 s.
Decoding on a thread of the user's Blender would therefore freeze its
interface. Instead, a separate factory-startup Blender started with
``--offline-mode``, ``--disable-autoexec`` and ``-noaudio`` runs the standalone
``waveform_worker.py``: Blender's audio module and its ffmpeg readers decode one
private file and numpy reduces the samples to 10 ms blocks. This module checks
those blocks against their frame count and folds them with ``EnvelopeBuilder``.
The child uses ``local_render``'s scrubbed environment, a disposable profile,
a timeout and cancellation that terminates it; its directory is always removed.
"""

import array
import json
import math
import os
import shutil
import stat
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ..audio_waveform import (
    BINS,
    ENVELOPE_MAX_BINS,
    ENVELOPE_MAX_CHANNELS,
    ENVELOPE_MAX_RATE,
    MAX_SECONDS,
    EnvelopeBuilder,
    WaveformCanceled,
    WaveformError,
)
from .local_render import LocalRenderError, RenderCancelled, _environment, _run, blender_path
from .transfers import TransferError
from .upload_sources import _open

FORMAT = 1
DECODE_TIMEOUT = 60.0
# Decoded float32 samples the child may hold: 256 MiB, enough for ten minutes
# of 48 kHz stereo. Longer, faster or wider audio fails instead of truncating.
MAX_DECODED_SAMPLES = 64 * 1024 * 1024
SOURCE_MAX_BYTES = 256 * 1024 * 1024
HEADER_MAX_BYTES = 4096
# Decode directories older than this were abandoned, for example by an exit mid-decode.
STALE_SECONDS = 24 * 60 * 60
# One float64 sum of squares and one float64 peak per 10 ms block.
_BLOCK_BYTES = 16
_ERRORS = {
    "unreadable": "Blender could not decode this audio",
    "unsupported": "This audio's sample rate or channel count is not supported",
    "empty": "This audio contains no samples",
    "too_long": "Audio exceeds the waveform duration limit",
    "invalid_samples": "Blender decoded invalid audio samples",
}
_INVALID = "The audio decoder returned an invalid waveform"


@dataclass(frozen=True)
class WaveformSpec:
    """The Blender executable and bundled worker, resolved on Blender's main thread."""

    binary: Path
    worker: Path
    timeout: float = DECODE_TIMEOUT
    max_samples: int = MAX_DECODED_SAMPLES

    def __post_init__(self):
        if any(
            not isinstance(path, Path) or not path.is_absolute()
            for path in (self.binary, self.worker)
        ):
            raise ValueError("Use absolute Blender executable and waveform worker paths")
        if (
            isinstance(self.timeout, bool)
            or not isinstance(self.timeout, (int, float))
            or not math.isfinite(self.timeout)
            or not 0 < self.timeout <= 600
        ):
            raise ValueError("Use a finite waveform decode timeout of at most 600 seconds")
        if type(self.max_samples) is not int or not 1 <= self.max_samples <= MAX_DECODED_SAMPLES:
            raise ValueError("Use a bounded decoded sample limit")


def source_stamp(path):
    """Identity of a regular, nonsymlink local audio file within the source size limit."""
    try:
        info = Path(path).lstat()
    except OSError:
        raise WaveformError("The audio file is missing or unreadable") from None
    if not stat.S_ISREG(info.st_mode):
        raise WaveformError("Choose a regular local audio file")
    if not 1 <= info.st_size <= SOURCE_MAX_BYTES:
        raise WaveformError("Audio waveforms support files from 1 byte to 256 MiB")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def sweep(directory, *, now=None, older_than=STALE_SECONDS):
    """Remove abandoned ``decode-*`` children of a caller's private directory.

    Only stale, nonsymlink directories with that prefix are removed; errors are
    ignored so a sweep never blocks a new decode.
    """
    now = time.time() if now is None else now
    try:
        children = tuple(Path(directory).iterdir())
    except OSError:
        return
    for child in children:
        try:
            info = child.lstat()
        except OSError:
            continue
        if (
            child.name.startswith("decode-")
            and stat.S_ISDIR(info.st_mode)
            and now - info.st_mtime > older_than
        ):
            shutil.rmtree(child, ignore_errors=True)


def _read(path, limit):
    try:
        stream, info = _open(path)
        with stream:
            if info.st_size > limit:
                raise WaveformError(_INVALID)
            data = stream.read(limit + 1)
    except (OSError, TransferError):
        raise WaveformError(_INVALID) from None
    if len(data) > limit:
        raise WaveformError(_INVALID)
    return data


def _failure(output):
    """The child's reported reason, from a fixed vocabulary; never its log."""
    try:
        value = json.loads(_read(output / "error.json", 256))
    except (WaveformError, ValueError):
        return _ERRORS["unreadable"]
    if not isinstance(value, dict) or value.get("format") != FORMAT:
        return _ERRORS["unreadable"]
    code = value.get("error")
    return (
        _ERRORS.get(code, _ERRORS["unreadable"]) if isinstance(code, str) else _ERRORS["unreadable"]
    )


def envelope(output, *, max_seconds=MAX_SECONDS, max_samples=MAX_DECODED_SAMPLES, bins=BINS):
    """Check the child's header and blocks, then fold them into an ``AudioEnvelope``."""
    try:
        header = json.loads(_read(output / "envelope.json", HEADER_MAX_BYTES))
    except ValueError:
        raise WaveformError(_INVALID) from None
    names = {"format", "sample_rate", "channels", "frames", "block"}
    if (
        not isinstance(header, dict)
        or set(header) != names
        or any(type(header[name]) is not int for name in names)
        or header["format"] != FORMAT
    ):
        raise WaveformError(_INVALID)
    rate, channels, frames = header["sample_rate"], header["channels"], header["frames"]
    if not 1 <= rate <= ENVELOPE_MAX_RATE or not 1 <= channels <= ENVELOPE_MAX_CHANNELS:
        raise WaveformError(_INVALID)
    if not 1 <= frames <= rate * max_seconds or frames * channels > max_samples:
        raise WaveformError(_INVALID)
    builder = EnvelopeBuilder(rate, channels, max_seconds=max_seconds)
    if header["block"] != builder.block:
        raise WaveformError(_INVALID)
    size = -(-frames // builder.block) * _BLOCK_BYTES
    data = _read(output / "blocks.bin", size)
    if len(data) != size:
        raise WaveformError(_INVALID)
    values = array.array("d")
    values.frombytes(data)
    if sys.byteorder != "little":
        values.byteswap()
    try:
        builder.add_blocks(values[0::2], values[1::2], frames)
        return builder.finish(bins)
    except WaveformError:
        raise WaveformError(_INVALID) from None


def decode(source, directory, spec, *, cancel=None, max_seconds=MAX_SECONDS, bins=BINS):
    """Decode one local audio file in an owned offline Blender child.

    ``directory`` is a private directory the caller owns; this call creates one
    ``decode-*`` child in it for the request, disposable profile, temporary
    files, log and output, and removes it on every exit. Errors name no path
    and carry no decoder output. The caller binds ``source`` to its bytes, for
    example with a receipt-checked private copy or ``source_stamp``.
    """
    if not isinstance(spec, WaveformSpec):
        raise TypeError("Use a waveform decoder specification")
    if type(max_seconds) is not int or not 1 <= max_seconds <= MAX_SECONDS:
        raise ValueError("Use a waveform duration limit of at most 600 seconds")
    if type(bins) is not int or not 1 <= bins <= ENVELOPE_MAX_BINS:
        raise ValueError("Use from 1 to 1024 waveform bins")
    cancel = cancel if cancel is not None else threading.Event()
    if cancel.is_set():
        raise WaveformCanceled("Waveform preview canceled")
    if not spec.binary.is_file() or not spec.worker.is_file():
        raise WaveformError("Audio waveforms need Blender's executable and bundled decoder")
    try:
        work = Path(tempfile.mkdtemp(prefix="decode-", dir=directory))
    except OSError:
        raise WaveformError("Waveform decoding storage is unavailable") from None
    try:
        profile, temporary, output = work / "profile", work / "tmp", work / "output"
        for path in (profile, temporary, output):
            path.mkdir(mode=0o700)
        request = work / "request.json"
        with request.open("x", encoding="utf-8") as stream:
            os.chmod(request, 0o600)
            json.dump(
                {
                    "format": FORMAT,
                    "source": blender_path(Path(source)),
                    "output": blender_path(output),
                    "max_seconds": max_seconds,
                    "max_samples": spec.max_samples,
                },
                stream,
            )
        command = [
            blender_path(spec.binary),
            "--offline-mode",
            "--factory-startup",
            "--disable-autoexec",
            "--background",
            "-noaudio",
            "--python-exit-code",
            "1",
            "--python",
            blender_path(spec.worker),
            "--",
            blender_path(request),
        ]
        started = time.monotonic()
        try:
            _run(
                command,
                log=work / "decode.log",
                env=_environment(profile, temporary),
                timeout=spec.timeout,
                cancel=cancel,
            )
        except RenderCancelled:
            raise WaveformCanceled("Waveform preview canceled") from None
        except LocalRenderError:
            if time.monotonic() - started >= spec.timeout:
                raise WaveformError("Waveform decoding timed out; use Retry") from None
            raise WaveformError(_failure(output)) from None
        if cancel.is_set():
            raise WaveformCanceled("Waveform preview canceled")
        return envelope(output, max_seconds=max_seconds, max_samples=spec.max_samples, bins=bins)
    except WaveformError:
        raise
    except (OSError, LocalRenderError):
        raise WaveformError("Waveform decoding could not start") from None
    finally:
        shutil.rmtree(work, ignore_errors=True)
