# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Status classification for local display records; no service operations."""

SUCCESS = {"success", "succeeded", "completed"}
FAILED = {"failure", "failed", "canceled", "cancelled", "error"}


def is_success(status):
    return (status or "").lower() in SUCCESS


def is_terminal(status):
    s = (status or "").lower()
    return s in SUCCESS or s in FAILED
