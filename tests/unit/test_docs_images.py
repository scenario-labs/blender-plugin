# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep real documentation assets under the same policy as the assets CLI."""

from pathlib import Path

from tools import docs_images

ROOT = Path(__file__).resolve().parents[2]


def test_documentation_images_follow_the_shared_policy():
    assert not docs_images.check(ROOT)
