# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender-side offline fixture for capture_gui.py; never submits service operations."""

import datetime
import importlib
import json
import os
import platform
import subprocess
import sys
import traceback
from pathlib import Path

import bpy
import gpu

OUTPUT, INSTALLED, VIEW, LANE, DELAY, FIXTURE, CAPTURE_BACKEND = sys.argv[
    sys.argv.index("--") + 1 :
]
OUTPUT = Path(OUTPUT)
FAILED = False


def view3d():
    window = bpy.context.window_manager.windows[0]
    area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
    return window, area, next(r for r in area.regions if r.type == "UI")


def guarded(callback):
    def run():
        global FAILED
        if FAILED:
            return None
        try:
            callback()
        except Exception:
            FAILED = True
            (OUTPUT / "gui.json").write_text(
                json.dumps({"status": "failed", "error": traceback.format_exc()})
            )
            traceback.print_exc()
            bpy.ops.wm.quit_blender()
        return None

    return run


def prepare():
    print("Capture GPU:", gpu.platform.backend_type_get(), gpu.platform.renderer_get(), flush=True)
    if bpy.app.online_access or os.environ.get("SCENARIO_GUI_PROBE") != "1":
        raise RuntimeError("Capture requires offline mode and the GUI probe guard")
    name = next(n for n in bpy.context.preferences.addons.keys() if n.endswith(".scenario"))
    module = importlib.import_module(name)
    if Path(module.__file__).resolve().parent != Path(INSTALLED).resolve():
        raise RuntimeError("Extension loaded outside verified installation")
    window, area, _ = view3d()
    area.spaces.active.show_region_ui = VIEW == "sidebar"
    runtime = importlib.import_module(name + ".blender.runtime")
    # All writable plugin paths remain inside this capture, including any manager
    # created by the ordinary GUI pump. These credentials are deliberately fake.
    runtime.prefs().output_dir = str(OUTPUT / "profile" / "outputs")
    if FIXTURE == "form":
        runtime.prefs().api_key = runtime.prefs().api_secret = "offline-screenshot-fixture"
        catalog = importlib.import_module(name + ".core.api.catalog")
        handlers = importlib.import_module(name + ".blender.handlers")
        record = catalog.ModelRecord.from_api(
            {
                "id": "model_offline-screenshot",
                "name": "Offline fixture",
                "type": "custom",
                "capabilities": [
                    {
                        "image": "txt2img",
                        "video": "txt2video",
                        "3d": "txt23d",
                        "audio": "txt2audio",
                    }[LANE]
                ],
                "inputs": [
                    {
                        "name": "prompt",
                        "type": "string",
                        "prompt": True,
                        "required": {"always": True},
                    },
                    {"name": "seed", "type": "integer", "default": 42},
                ],
            }
        )
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": [record], "detailed": [record]})
        )
        runtime.state.account_label = "Offline screenshot fixture"
    bpy.context.scene.scenario.lane = LANE
    bpy.context.scene.scenario.lane_state(
        LANE
    ).prompt = "A small ceramic robot tending a rooftop garden"
    if VIEW == "composer":
        state = runtime.state.composer
        state.expanded = True
        state.sync_from_lane(bpy.context.scene)
        state.focused = False
    area.tag_redraw()


def select():
    window, area, region = view3d()
    if VIEW == "sidebar":
        with bpy.context.temp_override(window=window, area=area, region=region):
            # Software-rendered CI can reach this timer before the first sidebar
            # draw. Blender keeps the dynamic category property read-only until
            # that draw has populated its enum items.
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
            region.active_panel_category = "Scenario"
            region.tag_redraw()
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
    area.tag_redraw()


def capture_x11(destination):
    """Read only this disposable Blender process's visible X11 window."""
    if sys.platform != "linux" or not os.environ.get("DISPLAY"):
        raise RuntimeError("X11 capture requires a Linux X display")
    found = subprocess.run(
        ["xdotool", "search", "--onlyvisible", "--pid", str(os.getpid())],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.split()
    if len(found) != 1 or not found[0].isdigit():
        raise RuntimeError("Expected exactly one visible window owned by this Blender process")
    subprocess.run(
        ["import", "-window", found[0], str(destination)],
        check=True,
        capture_output=True,
        timeout=10,
    )


def capture():
    window, area, region = view3d()
    if bpy.app.online_access:
        raise RuntimeError("Online access changed during capture")
    if VIEW == "sidebar" and (region.width <= 1 or region.active_panel_category != "Scenario"):
        raise RuntimeError("Scenario sidebar is not active")
    with bpy.context.temp_override(window=window, area=area):
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
        if CAPTURE_BACKEND == "blender":
            result = bpy.ops.screen.screenshot(filepath=str(OUTPUT / "plugin.png"))
            if result != {"FINISHED"}:
                raise RuntimeError("Blender screenshot operator did not finish")
        else:
            capture_x11(OUTPUT / "plugin.png")
    shot = bpy.data.images.load(str(OUTPUT / "plugin.png"), check_existing=False)
    try:
        dimensions = list(shot.size)
        # Xvfb without a window manager can return a valid but entirely black
        # front buffer. Sample RGB pixels (exclude alpha) before claiming capture.
        pixels = shot.pixels
        stride = max(4, (len(pixels) // 512 // 4) * 4)
        samples = {
            tuple(round(v, 3) for v in pixels[i : i + 3]) for i in range(0, len(pixels), stride)
        }
        if len(samples) < 2:
            raise RuntimeError("Screenshot is blank; check the display/window manager")
    finally:
        bpy.data.images.remove(shot)
    (OUTPUT / "gui.json").write_text(
        json.dumps(
            {
                "status": "captured",
                "captured_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "blender_version": list(bpy.app.version),
                "blender": bpy.app.version_string,
                "python": sys.version,
                "os": platform.platform(),
                "online_access": bpy.app.online_access,
                "view": VIEW,
                "lane": LANE,
                "fixture": FIXTURE,
                "active_sidebar": region.active_panel_category,
                "image_size": dimensions,
                "capture_backend": CAPTURE_BACKEND,
                "gpu_backend": gpu.platform.backend_type_get(),
                "gpu_renderer": gpu.platform.renderer_get(),
                "distinct_rgb_samples": len(samples),
            },
            indent=2,
        )
        + "\n"
    )
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(guarded(prepare), first_interval=1.5)
bpy.app.timers.register(guarded(select), first_interval=3)
bpy.app.timers.register(guarded(capture), first_interval=float(DELAY))
