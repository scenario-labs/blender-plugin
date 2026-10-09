# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone owned Blender process that reduces one audio file to level blocks.

``core.jobs.audio_decode`` starts it with ``--offline-mode``,
``--factory-startup``, ``--disable-autoexec``, ``--background`` and ``-noaudio``.
It does not import or register the extension. Blender's audio module decodes
the file named in the request from its start, without seeking, up to the
duration and sample limits; numpy then writes one sum of squares and one peak
of clamped samples per 10 ms block. A failure is reported as a fixed code in
``error.json``; the parent never reads this process's log.
"""

import json
import sys
from pathlib import Path

FORMAT = 1
MAX_REQUEST_BYTES = 4096
MAX_RATE = 192_000
MAX_CHANNELS = 8
# Blocks per numpy pass: about 3.5 MiB of float64 frames at 44.1 kHz stereo.
CHUNK_BLOCKS = 512


class DecodeFailure(Exception):
    """A reportable failure; ``code`` belongs to the parent's fixed vocabulary."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _request(path):
    if path.stat().st_size > MAX_REQUEST_BYTES:
        raise ValueError("Waveform request is too large")
    value = json.loads(path.read_text(encoding="utf-8"))
    names = {"format", "source", "output", "max_seconds", "max_samples"}
    if not isinstance(value, dict) or set(value) != names or value["format"] != FORMAT:
        raise ValueError("Use an owned waveform request")
    source, output = Path(value["source"]), Path(value["output"])
    if not source.is_absolute() or not output.is_absolute():
        raise ValueError("Use absolute waveform paths")
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise ValueError("The owned waveform output directory must be empty")
    limits = value["max_seconds"], value["max_samples"]
    if any(type(limit) is not int or limit < 1 for limit in limits):
        raise ValueError("Use positive waveform limits")
    return source, output, *limits


def reduce(data, rate, numpy):
    """Per-block sums of squares and peaks of samples clamped to full scale.

    ``data`` has one row per frame and one column per channel. Blocks hold
    ``rate // 100`` frames, at least one, and only the last may be partial.
    """
    frames = data.shape[0]
    block = max(1, rate // 100)
    result = numpy.empty((-(-frames // block), 2), dtype="<f8")
    step = block * CHUNK_BLOCKS
    for start in range(0, frames, step):
        chunk = numpy.asarray(data[start : start + step], dtype=numpy.float64)
        if not numpy.isfinite(chunk).all():
            raise DecodeFailure("invalid_samples")
        numpy.clip(chunk, -1.0, 1.0, out=chunk)
        offsets = numpy.arange(0, chunk.shape[0], block)
        rows = slice(start // block, start // block + len(offsets))
        result[rows, 0] = numpy.add.reduceat(numpy.square(chunk).sum(axis=1), offsets)
        result[rows, 1] = numpy.maximum.reduceat(numpy.abs(chunk).max(axis=1), offsets)
    return block, result


def decode(source, max_seconds, max_samples, aud, numpy):
    try:
        sound = aud.Sound(str(source))
        rate, channels = sound.specs
    except aud.error:
        raise DecodeFailure("unreadable") from None
    if rate != int(rate) or not 1 <= int(rate) <= MAX_RATE or not 1 <= channels <= MAX_CHANNELS:
        raise DecodeFailure("unsupported")
    rate = int(rate)
    limit = min(max_seconds * rate, max_samples // channels)
    if limit < 1:
        raise DecodeFailure("too_long")
    try:
        # Starting at zero never seeks; two extra frames reveal longer audio.
        data = sound.limit(0, (limit + 2) / rate).data()
    except aud.error:
        raise DecodeFailure("unreadable") from None
    if data.ndim != 2 or data.shape[1] != channels:
        raise DecodeFailure("unsupported")
    if not data.shape[0]:
        raise DecodeFailure("empty")
    if data.shape[0] > limit:
        raise DecodeFailure("too_long")
    block, blocks = reduce(data, rate, numpy)
    header = {
        "format": FORMAT,
        "sample_rate": rate,
        "channels": channels,
        "frames": int(data.shape[0]),
        "block": block,
    }
    return header, blocks


def main():
    import aud
    import numpy

    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 1:
        raise ValueError("Provide the owned waveform request")
    source, output, max_seconds, max_samples = _request(Path(arguments[0]))
    try:
        header, blocks = decode(source, max_seconds, max_samples, aud, numpy)
    except DecodeFailure as failure:
        with (output / "error.json").open("x", encoding="utf-8") as stream:
            json.dump({"format": FORMAT, "error": failure.code}, stream)
        raise
    with (output / "blocks.bin").open("xb") as stream:
        stream.write(blocks.tobytes())
    # The header is written last: the parent reads blocks only after it exists.
    with (output / "envelope.json").open("x", encoding="utf-8") as stream:
        json.dump(header, stream)


if __name__ == "__main__":
    main()
