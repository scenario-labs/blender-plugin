# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility entry point for the explicit quote/submit/resume Image check."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.smoke_image import main

if __name__ == "__main__":
    raise SystemExit(main())
