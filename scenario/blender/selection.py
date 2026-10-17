# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The selection and the active object, read the same way on the desktop and headless.

Blender started with `--background` on a saved file gives timers and commands a
context without `selected_objects` or `active_object`, while its view layer still
holds both. The local MCP server's headless command runs in that context."""


def selected_objects(context):
    """The selected objects, from `context.selected_objects` or else the context's view layer."""
    objects = getattr(context, "selected_objects", None)
    if objects is not None:
        return list(objects)
    layer = context.view_layer
    return [obj for obj in layer.objects if obj.select_get(view_layer=layer)]


def active_object(context):
    """The active object or None, from `context.active_object` or else the context's view layer."""
    if hasattr(context, "active_object"):
        return context.active_object
    return context.view_layer.objects.active
