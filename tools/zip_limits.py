# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared decompression limits for extension candidates and nested SDK wheels."""

MAX_MEMBERS = 10_000
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024
MAX_NOTICE_BYTES = 1024 * 1024


def check_archive(archive):
    """Reject excessive declared expansion before reading any member payload."""
    entries = archive.infolist()
    if len(entries) > MAX_MEMBERS:
        raise ValueError("Archive member count exceeds limit")
    if len({entry.filename for entry in entries}) != len(entries):
        raise ValueError("Archive has duplicate members")
    if any(entry.file_size > MAX_MEMBER_BYTES for entry in entries):
        raise ValueError("Archive member size exceeds limit")
    if sum(entry.file_size for entry in entries) > MAX_TOTAL_BYTES:
        raise ValueError("Archive expanded size exceeds limit")


def read_member(archive, name, *, limit):
    entry = archive.getinfo(name)
    if entry.file_size > limit:
        raise ValueError("Archive member size exceeds limit: " + name)
    with archive.open(entry) as member:
        data = member.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Archive member size exceeds limit: " + name)
    return data


def read_file(path, *, limit):
    if path.stat().st_size > limit:
        raise ValueError("Wheel file size exceeds limit")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Wheel file size exceeds limit")
    return data
