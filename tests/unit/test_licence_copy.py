# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The extension zip must carry the GPL text (GPLv3 section 4): scenario/LICENSE mirrors the root LICENSE."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_packaged_licence_is_a_byte_identical_copy_of_the_root_licence():
    root = (ROOT / "LICENSE").read_bytes()
    packaged = (ROOT / "scenario" / "LICENSE").read_bytes()
    assert packaged == root, "run: cp LICENSE scenario/LICENSE"
    assert b"GNU GENERAL PUBLIC LICENSE" in packaged
