# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify selected downloaded releases with GitHub, without building or publishing."""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from release_inventory import (
    MAX_ARCHIVE,
    MAX_METADATA,
    PREFIX,
    REPOSITORY,
    asset_metadata,
    checksums,
    published_releases,
)
from repository import read_archive, read_inventory, verify_bytes, write_json

WORKFLOW = f"{REPOSITORY}/.github/workflows/release-please.yml"
PREDICATE = "https://slsa.dev/provenance/v1"


class GitHub:
    """Use the authenticated GitHub CLI, with no shell or displayed remote output."""

    def run(self, arguments, limit=10 * MAX_METADATA):
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("SCENARIO_") and key != "GH_DEBUG"
        }
        environment["GH_PROMPT_DISABLED"] = "1"
        # Keep CLI output out of process memory until its parse-size check. The
        # timeout bounds the command, not temporary output growth inside gh.
        with tempfile.TemporaryFile() as output:
            try:
                result = subprocess.run(
                    ["gh", *arguments, "--hostname", "github.com"],
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.DEVNULL,
                    env=environment,
                    timeout=180,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                raise ValueError("GitHub command unavailable or timed out") from None
            if result.returncode:
                raise ValueError("GitHub read or attestation verification failed")
            output.seek(0)
            content = output.read(limit + 1)
        if not content or len(content) > limit:
            raise ValueError("GitHub returned empty or excessive output")
        return content

    def read(self, endpoint):
        return json.loads(self.run(["api", f"repos/{REPOSITORY}/{endpoint}"], MAX_METADATA))

    def checksum(self, asset):
        identifier = asset.get("id")
        if type(identifier) is not int or identifier < 1:
            raise ValueError("Checksum asset requires a positive GitHub asset id")
        return self.run(
            [
                "api",
                f"repos/{REPOSITORY}/releases/assets/{identifier}",
                "--header",
                "Accept: application/octet-stream",
            ],
            MAX_METADATA,
        )

    def verify(self, path, commit):
        result = json.loads(
            self.run(
                [
                    "attestation",
                    "verify",
                    str(path),
                    "--repo",
                    REPOSITORY,
                    "--signer-workflow",
                    WORKFLOW,
                    "--source-digest",
                    commit,
                    "--signer-digest",
                    commit,
                    "--source-ref",
                    "refs/heads/main",
                    "--predicate-type",
                    PREDICATE,
                    "--deny-self-hosted-runners",
                    "--format",
                    "json",
                ]
            )
        )
        if (
            not isinstance(result, list)
            or not result
            or any(not isinstance(x, dict) for x in result)
        ):
            raise ValueError("GitHub returned no verified attestations")


def tag_commit(github, tag):
    reference = github.read(f"git/ref/tags/{tag}")
    if not isinstance(reference, dict) or reference.get("ref") != f"refs/tags/{tag}":
        raise ValueError("GitHub returned a different tag reference")
    seen = set()
    for _ in range(8):
        target = reference.get("object")
        if not isinstance(target, dict):
            raise ValueError("Tag has no valid target")
        digest = target.get("sha")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{40}", digest):
            raise ValueError("Tag target requires a full Git commit digest")
        if target.get("type") == "commit":
            return digest
        if target.get("type") != "tag" or digest in seen:
            raise ValueError("Tag does not resolve to a commit")
        seen.add(digest)
        reference = github.read(f"git/tags/{digest}")
        if not isinstance(reference, dict) or reference.get("sha") != digest:
            raise ValueError("GitHub returned a different annotated tag")
    raise ValueError("Tag nesting exceeds the verification limit")


def release_assets(github, tag, archive, scratch):
    release = github.read(f"releases/tags/{tag}")
    write_json(scratch, [[release]])
    rows = published_releases(scratch)
    if len(rows) != 1 or rows[0]["tag_name"] != tag:
        raise ValueError("GitHub returned a different published release")
    package = asset_metadata(release, archive["file"], MAX_ARCHIVE)
    checksum = asset_metadata(release, "SHA256SUMS", MAX_METADATA)
    if package["size"] != archive["size"]:
        raise ValueError("Selected archive size differs from the published asset")
    # Download counts and body edits are not asset identity. Replacements,
    # withdrawals and changes to publication/asset metadata do require a retry.
    identity = {
        "release": [release.get(key) for key in ("id", "tag_name", "published_at")],
        "assets": [
            {key: asset.get(key) for key in ("id", "name", "size", "updated_at", "digest")}
            for asset in (package, checksum)
        ],
    }
    return checksum, identity


def verify(inventory_path, output, *, github=None):
    if output.exists() or output.is_symlink():
        raise ValueError("Verification output already exists; choose a new directory")
    if inventory_path.is_symlink():
        raise ValueError("Use a regular inventory file")
    inventory = read_inventory(inventory_path)
    if inventory["extension_id"] != "scenario":
        raise ValueError("Use the Scenario release inventory")
    for archive in inventory["archives"]:
        if archive["file"] != f"scenario-{archive['version']}.zip":
            raise ValueError("Archive name must match the adopted release version")
        read_archive(inventory_path.parent / archive["file"], archive, "scenario")
    github = github or GitHub()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".verify-releases-", dir=output.parent) as temporary:
        root = Path(temporary)
        staged = root / "verified"
        staged.mkdir()
        records = []
        observed = []
        for archive in inventory["archives"]:
            tag = PREFIX + archive["version"]
            target = staged / archive["file"]
            shutil.copyfile(inventory_path.parent / archive["file"], target)
            verify_bytes(target, archive)
            checksum, identity = release_assets(github, tag, archive, root / "release.json")
            commit = tag_commit(github, tag)
            sums = root / "SHA256SUMS"
            sums.write_bytes(github.checksum(checksum))
            if checksums(sums, checksum["size"]).get(archive["file"]) != archive["sha256"]:
                raise ValueError("Published checksum differs from the selected archive")
            github.verify(sums, commit)
            github.verify(target, commit)
            verify_bytes(target, archive)
            records.append({"tag": tag, "commit": commit, **archive})
            observed.append((tag, archive, commit, identity))
        # Recheck the whole selected set after all potentially slow provenance
        # calls, including releases verified earlier in a multi-release batch.
        for tag, archive, commit, identity in observed:
            verify_bytes(staged / archive["file"], archive)
            _, current = release_assets(github, tag, archive, root / "release.json")
            if current != identity or tag_commit(github, tag) != commit:
                raise ValueError("Release or tag changed during verification; refresh and retry")
        write_json(staged / "inventory.json", inventory)
        write_json(
            staged / "provenance.json",
            {
                "schema_version": 1,
                "repository": REPOSITORY,
                "workflow": WORKFLOW,
                "verified_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "releases": records,
            },
        )
        if output.exists() or output.is_symlink():
            raise ValueError("Verification output appeared during preparation")
        staged.rename(output)
    return output / "inventory.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New verified-assets directory")
    args = parser.parse_args()
    try:
        print(f"Verified inventory: {verify(args.inventory, args.output)}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        # Never echo CLI output, remote metadata or credential-bearing diagnostics.
        print(
            "Release verification failed; check inventory, GitHub access and provenance",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
