# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Internal update probe, invoked only by tools/test_repository_update.py."""

import argparse
import importlib
import json
import os
import pathlib
import sys
import urllib.parse


def main():
    raw_profile = os.environ.get("BLENDER_USER_RESOURCES")
    if not raw_profile:
        raise RuntimeError("Use tools/test_repository_update.py with its disposable profile")
    profile = pathlib.Path(raw_profile).resolve()
    marker = profile.parent / "repository-update.json"
    if not marker.is_file() or json.loads(marker.read_text()).get("profile") != str(profile):
        raise RuntimeError("Refusing an unmanaged Blender profile")
    import bpy

    if pathlib.Path(bpy.utils.resource_path("USER")).resolve() != profile:
        raise RuntimeError("Blender did not use the disposable profile")
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--report", required=True, type=pathlib.Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    url = urllib.parse.urlsplit(args.url)
    if (
        url.scheme != "http"
        or url.hostname != "127.0.0.1"
        or not url.port
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path != "/index.json"
    ):
        raise RuntimeError("Only a local fixture repository is allowed")
    if args.report.resolve().parent != profile.parent:
        raise RuntimeError("Report must belong to this run")
    repos = bpy.context.preferences.extensions.repos
    if len(repos) != 1 or repos[0].module != "update_fixture" or repos[0].remote_url != args.url:
        raise RuntimeError("Only this run's loopback repository may be configured")
    module_name = "bl_ext.update_fixture.scenario"

    def check(version):
        if module_name not in bpy.context.preferences.addons:
            raise RuntimeError("Synthetic extension is no longer enabled")
        module = importlib.import_module(module_name)
        if (
            pathlib.Path(module.__file__).resolve()
            != profile / "extensions/update_fixture/scenario/__init__.py"
        ):
            raise RuntimeError("Synthetic extension loaded outside this profile")
        if (
            module.VERSION != version
            or bpy.types.WindowManager.scenario_update_fixture_version != version
        ):
            raise RuntimeError("Native update did not register the expected extension version")

    check("1.0.0")
    if bpy.ops.extensions.repo_sync_all() != {"FINISHED"}:
        raise RuntimeError("Native repository sync failed")
    if bpy.ops.extensions.package_upgrade_all() != {"FINISHED"}:
        raise RuntimeError("Native extension update failed")
    check("2.0.0")
    args.report.write_text(
        json.dumps({"before": "1.0.0", "after": "2.0.0", "enabled": True}) + "\n"
    )


if __name__ == "__main__":
    main()
