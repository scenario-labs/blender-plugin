# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The real release publication predicate must require the handbook and provenance bundle."""

import json
import re
import subprocess
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/release-please.yml"


@pytest.mark.parametrize("missing", [None, "zip", "handbook", "sums", "bundle"])
def test_publish_gate_rejects_incomplete_release_assets(missing):
    text = WORKFLOW.read_text()
    publish = text.split("  publish:\n", 1)[1].split("  release-pr:\n", 1)[0]
    predicate = re.search(r"jq -e .*? '\n(.*?)\n          ' <<<", publish, re.S)[1]
    names = {
        "zip": "scenario-1.0.0.zip",
        "handbook": "scenario-handbook-1.0.0.html",
        "sums": "SHA256SUMS",
        "bundle": "scenario-1.0.0.sigstore.json",
    }
    result = subprocess.run(
        [
            "jq",
            "-e",
            "--arg",
            "sha",
            "a" * 40,
            "--arg",
            "zip",
            names["zip"],
            "--arg",
            "handbook",
            names["handbook"],
            "--arg",
            "bundle",
            names["bundle"],
            predicate,
        ],
        input=json.dumps(
            {
                "isDraft": True,
                "targetCommitish": "a" * 40,
                "assets": [{"name": name} for key, name in names.items() if key != missing],
            }
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if missing is None else 1)


def test_handbook_is_built_checksummed_attested_and_attached_before_publication():
    text = WORKFLOW.read_text()
    assets = text.split("  assets:\n", 1)[1].split("  validate:\n", 1)[0]
    assert (
        'tools/build_docs_html.py --inline-images --output "dist/scenario-handbook-${VERSION}.html"'
        in assets
    )
    assert 'sha256sum "scenario-${VERSION}.zip" "scenario-handbook-${VERSION}.html"' in assets
    attested = assets.split("subject-path: |", 1)[1].split("- uses:", 1)[0]
    assert "dist/scenario-handbook-${{ env.VERSION }}.html" in attested
    upload = next(line for line in assets.splitlines() if 'gh release upload "$TAG"' in line)
    assert '"dist/scenario-handbook-${VERSION}.html"' in upload
    assert "needs: [release-please, assets, validate]" in text


def test_provenance_bundle_is_attached_before_publication():
    text = WORKFLOW.read_text()
    assets = text.split("  assets:\n", 1)[1].split("  validate:\n", 1)[0]
    attest = assets.split("actions/attest-build-provenance@", 1)[1].split("- uses:", 1)[0]
    assert "id: provenance" in attest
    assert "BUNDLE: ${{ steps.provenance.outputs.bundle-path }}" in assets
    assert 'cp "$BUNDLE" "dist/scenario-${VERSION}.sigstore.json"' in assets
    upload = next(line for line in assets.splitlines() if 'gh release upload "$TAG"' in line)
    assert '"dist/scenario-${VERSION}.sigstore.json"' in upload
