# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit model quote/submit/resume checks; see tests/smoke/README.md."""

from tools.smoke_image import main

if __name__ == "__main__":
    raise SystemExit(main(default_result_kind=None))
