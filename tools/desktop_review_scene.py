# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare a recognizable scene and observe identity without simulating UI input."""

import json
import os
import sys
import time
from pathlib import Path

import bpy


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def main():
    directory, mode = sys.argv[sys.argv.index("--") + 1 :]
    directory = Path(directory)
    config = json.loads((directory / "review.json").read_text())
    profile = Path(config["profile"])
    if Path(bpy.utils.user_resource("CONFIG")).resolve() != profile / "config":
        raise RuntimeError("Review process is outside the selected profile")
    module = sys.modules.get("bl_ext.user_default.scenario")
    if module is None or Path(module.__file__).parent.resolve() != Path(config["installed"]):
        raise RuntimeError("The exact installed extension is not loaded")
    if bpy.app.online_access:
        raise RuntimeError("Review requires offline Blender")
    if mode == "prepare":
        bpy.context.preferences.view.show_splash = False
        bpy.ops.wm.save_userpref()
        bpy.context.scene.name = "Scenario Desktop Review"
        bpy.ops.wm.save_as_mainfile(filepath=config["fixture"])
        return
    if mode != "observe" or bpy.data.filepath != config["fixture"]:
        raise RuntimeError("Unexpected review mode or scene")
    # This is an additional Python guard, not an OS network sandbox.
    violations = []

    def deny_network(event, _args):
        if event in ("socket.connect", "socket.bind"):
            violations.append(event)
            raise RuntimeError("Offline desktop review rejects network activity")

    sys.addaudithook(deny_network)
    ready = {
        "pid": os.getpid(),
        "profile": str(profile),
        "extension": module.__file__,
        "file": bpy.data.filepath,
        "online_access": bpy.app.online_access,
        "blender_version": list(bpy.app.version),
    }
    write_json(directory / "ready.json", ready)
    deadline = time.monotonic() + config["duration"]

    def observe():
        write_json(
            directory / "observed.json",
            {
                **ready,
                "online_access": bpy.app.online_access,
                "frame": bpy.context.scene.frame_current,
                "network_violations": violations,
            },
        )
        if time.monotonic() >= deadline or (directory / "stop").exists():
            bpy.ops.wm.quit_blender()
            return None
        return 0.5

    bpy.app.timers.register(observe, first_interval=0.5)


if __name__ == "__main__":
    main()
