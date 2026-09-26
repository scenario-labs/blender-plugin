# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit repository setup and update checks through Blender's native manager."""

import bpy

from .. import __version__

GUIDE_URL = "https://blender.scenario.com/"
REPOSITORY_URL = GUIDE_URL + "repo/index.json"
RELEASES_URL = "https://github.com/scenario-labs/blender-plugin/releases"


def official_repository(context):
    for index, repository in enumerate(context.preferences.extensions.repos):
        if repository.use_remote_url and repository.remote_url.rstrip("/") == REPOSITORY_URL:
            return index, repository
    return -1, None


class SCENARIO_OT_setup_updates(bpy.types.Operator):
    bl_idname = "scenario.setup_updates"
    bl_label = "Set up official repository"
    bl_description = "Add the official Scenario repository to Blender's extension manager"

    @classmethod
    def poll(cls, context):
        if not bpy.app.online_access:
            cls.poll_message_set("Enable Allow Online Access in Blender's System preferences")
            return False
        return True

    def execute(self, context):
        if not bpy.app.online_access:
            self.report({"WARNING"}, "Allow Online Access is off")
            return {"CANCELLED"}
        _, repository = official_repository(context)
        if repository is None:
            result = bpy.ops.preferences.extension_repo_add(
                "EXEC_DEFAULT",
                name="Scenario",
                remote_url=REPOSITORY_URL,
                use_sync_on_startup=False,
            )
            if "FINISHED" not in result:
                return result
            _, repository = official_repository(context)
        if repository is None:
            self.report({"ERROR"}, "Open Get Extensions to inspect repository setup")
            return {"CANCELLED"}
        repository.enabled = True
        self.report({"INFO"}, "Repository configured; check for updates in Blender")
        return {"FINISHED"}


class SCENARIO_OT_check_updates(bpy.types.Operator):
    bl_idname = "scenario.check_updates"
    bl_label = "Check for updates"
    bl_description = "Refresh the official repository in Blender without installing an update"

    @classmethod
    def poll(cls, context):
        if not bpy.app.online_access:
            cls.poll_message_set("Enable Allow Online Access in Blender's System preferences")
            return False
        _, repository = official_repository(context)
        if repository is None or not repository.enabled:
            cls.poll_message_set("Set up and enable the official repository first")
            return False
        return True

    def execute(self, context):
        if not self.poll(context):
            return {"CANCELLED"}
        index, _ = official_repository(context)
        return bpy.ops.extensions.repo_sync(
            "EXEC_DEFAULT" if bpy.app.background else "INVOKE_DEFAULT", repo_index=index
        )


def draw(layout, context):
    box = layout.box()
    box.label(text="Updates", icon="FILE_REFRESH")
    box.label(text=f"Installed version: {__version__}")
    _, repository = official_repository(context)
    if repository is None:
        box.label(text="Official repository is not configured", icon="INFO")
    elif not repository.enabled:
        box.label(text="Official repository is disabled", icon="INFO")
    else:
        box.label(text="Official repository is configured", icon="CHECKMARK")
    if not bpy.app.online_access:
        box.label(text="Allow Online Access is off in System preferences", icon="INFO")
    row = box.row(align=True)
    if repository is None or not repository.enabled:
        row.operator("scenario.setup_updates", icon="ADD")
    else:
        row.operator("scenario.check_updates", icon="FILE_REFRESH")
    box.operator(
        "screen.userpref_show", text="Open Get Extensions", icon="PREFERENCES"
    ).section = "EXTENSIONS"
    # Repository namespaces determine both add-on preferences and extension storage.
    # Never claim that adding a remote repository migrates a local ZIP installation.
    installed_repository = __package__.split(".")[1] if __package__.startswith("bl_ext.") else ""
    if repository is not None and installed_repository != repository.module:
        box.label(text="This copy was installed outside the official repository", icon="INFO")
        box.label(text="Use a release ZIP to update this copy and retain its settings")
    box.label(text="Choose updates in Get Extensions; restart Blender if requested")
    row = box.row(align=True)
    row.operator("wm.url_open", text="Update guide", icon="HELP").url = GUIDE_URL + "#updates"
    row.operator("wm.url_open", text="Release ZIPs", icon="URL").url = RELEASES_URL


CLASSES = (SCENARIO_OT_setup_updates, SCENARIO_OT_check_updates)
