# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fuzz which local files a connected agent may upload: ``allowed_upload``.

Each input builds a private temporary tree with an allowed folder, an outside folder,
links between them, a link loop and look-alike names, removed when the input ends.
An allowed path must be an absolute, link-free path to a regular file that is either
physically inside a resolved allowed folder or a file the user chose. The oracle
compares device and inode numbers, not path text, so case folding and Unicode
normalization on the host file system cannot hide an escape.
"""

import os
import stat
import sys
import tempfile
import unicodedata
from pathlib import Path

from support import DataProvider, split

from scenario.mcp.upload_policy import ChosenFiles, UploadRefused, allowed_upload, resolve_file

PROVIDER = DataProvider
CAFE = "café.bin"
FILES = ("allowed/a.bin", "allowed/sub/b.bin", f"allowed/{CAFE}", "outside/secret.bin")
FILES += ("outside/chosen.bin", "outside/deep/x.bin", "allowed-twin/a.bin")
LINKS = (
    ("allowed/link_in", "a.bin"),
    ("allowed/link_out", "../outside/secret.bin"),
    ("allowed/dir_out", "../outside"),
    ("allowed/loop", "loop2"),
    ("allowed/loop2", "loop"),
    ("allowed/sub/up", ".."),
    ("allowed/dangling", "missing.bin"),
    ("outside/back", "../allowed/a.bin"),
    ("rootlink", "allowed"),
)
PARTS = ["allowed", "outside", "allowed-twin", "sub", "deep", "a.bin", "b.bin", "secret.bin"]
PARTS += ["chosen.bin", "x.bin", "link_in", "link_out", "dir_out", "loop", "up", "dangling"]
PARTS += ["back", "rootlink", "fifo", "..", ".", "", CAFE, unicodedata.normalize("NFD", CAFE)]
PARTS += ["ALLOWED", "A.BIN", "a.bin\x00", "a.bin ", "a.bin.", "x" * 300, "․․"]
ROOTS = ["allowed", "rootlink", "allowed/sub", "allowed/a.bin", "missing", "", "outside/back"]
# Paths that name something in the tree; mutations then add the hostile parts.
TARGETS = [*FILES, *(name for name, _ in LINKS), "allowed/dir_out/secret.bin", "rootlink/a.bin"]
TARGETS += ["rootlink/sub/b.bin", "allowed/sub/up/a.bin", "allowed/sub/up/link_out", "allowed/fifo"]
TARGETS += ["allowed/sub", "allowed/sub/../../outside/secret.bin"]


def build(base):
    for name in FILES:
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
    for name, target in LINKS:
        try:
            os.symlink(target, base / name)
        except (OSError, NotImplementedError):
            pass  # Windows without the symlink privilege: the tree has no links.
    if hasattr(os, "mkfifo"):
        os.mkfifo(base / "allowed" / "fifo")


def inside(folder):
    """Device and inode of every regular file physically under ``folder``, links unfollowed."""
    found = set()
    for directory, _, names in os.walk(folder, followlinks=False):
        for name in names:
            info = os.lstat(os.path.join(directory, name))
            if stat.S_ISREG(info.st_mode):
                found.add((info.st_dev, info.st_ino))
    return found


def raw_path(fdp, base):
    start = fdp.ConsumeIntInRange(0, 7)
    if start >= 5:
        parts = [fdp.PickValueInList(PARTS) for _ in range(fdp.ConsumeIntInRange(0, 6))]
    else:
        parts = fdp.PickValueInList(TARGETS).split("/")
        for _ in range(fdp.ConsumeIntInRange(0, 2)):
            parts.insert(fdp.ConsumeIntInRange(0, len(parts)), fdp.PickValueInList(PARTS))
    separator = fdp.PickValueInList(["/", "//", os.sep, "/./"])
    tail = separator.join(parts)
    if start == 0:
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 40))
    if start == 1:
        return "~fuzz-no-such-user/" + tail
    if start == 2:
        return Path(base, *[part for part in parts if part and "\x00" not in part])
    if start == 3:
        return fdp.PickValueInList([None, 3, b"/etc/passwd", object()])
    return str(base) + separator + tail


def TestOneInput(data):
    _, rest = split(data)
    fdp = PROVIDER(rest)
    with tempfile.TemporaryDirectory(prefix="fuzz-upload-") as temporary:
        base = Path(os.path.realpath(temporary))
        build(base)
        roots = [str(base / fdp.PickValueInList(ROOTS)) for _ in range(fdp.ConsumeIntInRange(0, 3))]
        allowed = set()
        for root in roots:
            folder = os.path.realpath(root)
            if os.path.isdir(folder):
                allowed |= inside(folder)
        limit = fdp.ConsumeIntInRange(1, 3)
        chosen, recorded = ChosenFiles(limit=limit), []
        for _ in range(fdp.ConsumeIntInRange(0, 4)):
            path = chosen.record(raw_path(fdp, base))
            if path is not None:
                assert path == resolve_file(path), "a choice is recorded resolved"
                recorded.append(path)
        assert len(chosen) <= limit, "old choices are forgotten past the limit"
        remembered = set()
        for path in recorded:
            if path in chosen:
                info = os.stat(path)
                remembered.add((info.st_dev, info.st_ino))
        for _ in range(fdp.ConsumeIntInRange(1, 4)):
            raw = raw_path(fdp, base)
            try:
                path = allowed_upload(raw, roots=roots, chosen=chosen)
            except UploadRefused:
                continue
            assert isinstance(path, Path) and path.is_absolute(), f"{raw!r} -> {path!r}"
            assert os.path.realpath(path) == str(path), f"{raw!r} -> {path!r} keeps a link"
            info = os.stat(path)
            assert stat.S_ISREG(info.st_mode), f"{raw!r} -> {path!r} is not a regular file"
            identity = (info.st_dev, info.st_ino)
            assert identity in allowed or identity in remembered, f"{raw!r} -> {path!r} escapes"


if __name__ == "__main__":
    import atheris

    PROVIDER = atheris.FuzzedDataProvider
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
