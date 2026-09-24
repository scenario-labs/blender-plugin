# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Disposable issue #27 acceptance probe; this file must never merge."""

import pytest


def test_expected_ci_acceptance_failure():
    pytest.fail("Intentional issue #27 gate proof; close this draft PR without merging")
