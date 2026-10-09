# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit experimental status for model capabilities whose result handling is not accepted.

Display only: a status never blocks a model. Its jobs still run and their results
stay in saved jobs. Generic import is offered by file type, so a returned GLB or
media file may be imported, but speech-to-text and video-to-motion handling has
not been accepted (#190).
"""

UNACCEPTED_CAPABILITIES = {"audio2txt": "speech-to-text", "video23d": "video-to-motion"}


def model_status(capabilities):
    """Short status for a model offering an unaccepted capability, or ""."""
    offered = {str(capability).lower() for capability in capabilities or ()}
    names = [name for capability, name in UNACCEPTED_CAPABILITIES.items() if capability in offered]
    return f"Experimental: {', '.join(names)} not accepted" if names else ""
