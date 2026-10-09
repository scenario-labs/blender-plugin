# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit experimental status for model capabilities without Blender application.

Display only: a status never blocks a model. Its jobs still run and their results
stay saved. Speech-to-text and video-to-motion result handling is tracked in #190.
"""

UNAPPLIED_CAPABILITIES = {"audio2txt": "speech-to-text", "video23d": "video-to-motion"}


def model_status(capabilities):
    """Short status for a model offering a capability without Blender application, or ""."""
    offered = {str(capability).lower() for capability in capabilities or ()}
    names = [name for capability, name in UNAPPLIED_CAPABILITIES.items() if capability in offered]
    return f"Experimental: {', '.join(names)} result stays saved" if names else ""
