# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Internal check that a predecessor's own storage code refuses an upgraded job store.

Only tools/test_repository_update.py invokes it, with factory settings so no
installed Scenario extension loads. Storage code comes from the exact predecessor
ZIP, imported under a private package name; the candidate never opens the file here.
"""

import argparse
import importlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

PACKAGE = "scenario_predecessor"
REFUSAL = "Unsupported job database format"


def extract(package, directory):
    """Copy only the predecessor's top-level module and pure `core` sources."""
    root = Path(directory) / PACKAGE
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            name = PurePosixPath(info.filename)
            if (
                info.is_dir()
                or name.is_absolute()
                or ".." in name.parts
                or name.suffix != ".py"
                or (name.parts[0] != "core" and str(name) != "__init__.py")
            ):
                continue
            target = root.joinpath(*name.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    if not (root / "core/jobs/store.py").is_file():
        raise RuntimeError("Predecessor has no shared job store")
    return root


def reopen(package, database):
    """Open `database` with the predecessor's JobStore; it must refuse without writing."""
    database = Path(database).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="predecessor-") as directory:
        root = extract(package, directory)
        sys.path.insert(0, str(root.parent))
        dont_write = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            store = importlib.import_module(f"{PACKAGE}.core.jobs.store")
            if not Path(store.__file__).resolve().is_relative_to(root.resolve()):
                raise RuntimeError("Predecessor storage was imported from elsewhere")
            scope = store.JobScope("https://predecessor.invalid/v1", "predecessor-reopen")
            try:
                store.JobStore(database, scope)
            except store.StoreError as error:
                message = str(error)
            else:
                raise RuntimeError("Predecessor storage opened the upgraded job store")
            if REFUSAL not in message:
                raise RuntimeError("Predecessor storage failed for another reason")
            return {"predecessor_schema": store._VERSION, "refused": message}
        finally:
            sys.dont_write_bytecode = dont_write
            sys.path.remove(str(root.parent))
            for name in [name for name in sys.modules if name.split(".")[0] == PACKAGE]:
                del sys.modules[name]


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from repository_update import owned_profile

    profile = owned_profile()
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.report.resolve().parent != profile.parent or not args.database.resolve(
        strict=True
    ).is_relative_to(profile):
        raise RuntimeError("Use only this run's profile database and report")
    if args.package.resolve().parent.parent != profile.parent:
        raise RuntimeError("Use only this run's predecessor package")
    args.report.write_text(json.dumps(reopen(args.package, args.database)) + "\n")


if __name__ == "__main__":
    main()
