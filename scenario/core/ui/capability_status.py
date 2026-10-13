# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit experimental status for model capabilities whose result handling is not accepted.

Display only: a status never blocks a model. Its jobs still run and their results
stay in saved jobs. Generic import is offered by file type, so a returned model
(GLB, glTF, FBX, OBJ or mesh PLY) or media file may be imported, but
speech-to-text and video-to-motion handling has not been accepted (#190).
"""

UNACCEPTED_CAPABILITIES = {"audio2txt": "speech-to-text", "video23d": "video-to-motion"}


def label(subject=""):
    """The status line of a capability that runs but is still in testing.

    It must read as experimental, never as a refusal: "not accepted" on its own
    read as if the service refused the model, although it runs. Without a
    subject, where a section title already names the capability, the line is
    the short "Experimental: in testing".
    """
    return f"Experimental: {subject} in testing" if subject else "Experimental: in testing"


def model_status(capabilities):
    """Short status for a model offering an unaccepted capability, or ""."""
    offered = {str(capability).lower() for capability in capabilities or ()}
    names = [name for capability, name in UNACCEPTED_CAPABILITIES.items() if capability in offered]
    return label(", ".join(names)) if names else ""
