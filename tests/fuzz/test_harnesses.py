# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every fuzz harness, run without Atheris on its seeds and a fixed pseudo-random corpus.

ClusterFuzzLite does the coverage-guided fuzzing; this keeps each harness importable,
its seeds on the parsers' success paths and its properties true in the unit run.
"""

import importlib
import json
import random
import re
import tempfile
import tomllib
import tracemalloc
from pathlib import Path

import pytest
import samples

from scenario.core.jobs import audio_decode, mp4_inspection
from scenario.core.scene import glb, model_formats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HARNESSES = sorted(path.stem for path in HERE.glob("fuzz_*.py"))
# Each upload input builds and removes a file tree, so it gets fewer inputs.
COUNTS = {"fuzz_upload_policy": 1500}
SIZES = (0, 1, 4, 16, 64, 256, 1024)
PEAK_BYTES = 16 * 1024 * 1024


def corpus(name, count):
    """The harness's seeds, then mutated seeds and random inputs from a fixed seed."""
    rng = random.Random(name)
    seeds = samples.seeds()[name]
    yield from seeds
    for _ in range(count):
        if rng.random() < 0.5:
            data = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 4)):
                position = rng.randrange(1, len(data) + 1)
                operation = rng.randrange(3)
                if operation == 0 and position < len(data):
                    data[position] = rng.randrange(256)
                elif operation == 1:
                    del data[position:]
                else:
                    data[position:position] = rng.randbytes(rng.choice(SIZES))
            yield bytes(data)
        else:
            yield bytes([rng.randrange(256)]) + rng.randbytes(rng.choice(SIZES))


def run(name, count):
    harness = importlib.import_module(name)
    for data in corpus(name, count):
        try:
            harness.TestOneInput(data)
        except Exception as error:
            raise AssertionError(f"{name} failed on input {data!r}: {error!r}") from error
        yield data


@pytest.mark.parametrize("name", HARNESSES)
def test_harness_properties_hold(name):
    assert sum(1 for _ in run(name, COUNTS.get(name, 3000))) > len(samples.seeds()[name])


@pytest.mark.parametrize("name", HARNESSES)
def test_harness_memory_is_bounded_by_its_input(name):
    """A length field must not drive an allocation: inputs here stay under a few KiB."""
    tracemalloc.start()
    try:
        for _ in run(name, 200):
            _, peak = tracemalloc.get_traced_memory()
            assert peak <= PEAK_BYTES, f"{name} allocated {peak} bytes"
            tracemalloc.reset_peak()
    finally:
        tracemalloc.stop()


def test_every_harness_has_seeds():
    assert HARNESSES and set(samples.seeds()) == set(HARNESSES)


def test_seeds_reach_the_parsers_success_paths(tmp_path):
    assert glb.inspect_glb(samples.glb(samples.STATIC_GLTF))["nodes"]
    assert glb.inspect_glb(samples.glb(samples.RIGGED_GLTF), static_only=False)["skins"]
    path = tmp_path / "movie.mp4"
    path.write_bytes(samples.mp4())
    summary = mp4_inspection.inspect(path)
    assert (summary.video[0].codec, summary.audio[0].codec) == ("h264", "aac")
    assert model_formats.inspect_ply_header(samples.MESH_PLY).kind == "mesh"
    splat = samples.splat_ply()
    assert model_formats.inspect_ply_header(splat, size=len(splat)).kind == "splat"
    for rate, channels, frames in ((48000, 2, 960), (100, 1, 7)):
        header, blocks = samples.decoder_output(rate, channels, frames)
        (tmp_path / "envelope.json").write_bytes(header)
        (tmp_path / "blocks.bin").write_bytes(blocks)
        assert audio_decode.envelope(tmp_path).sample_rate == json.loads(header)["sample_rate"]


def test_seed_corpora_are_written_per_harness():
    with tempfile.TemporaryDirectory() as directory:
        samples.write_corpora(directory)
        names = sorted(path.name for path in Path(directory).iterdir())
    assert names == [f"{name}_seed_corpus.zip" for name in HARNESSES]


def test_fuzz_image_requirements_match_the_lock():
    """The fuzz image installs these exact hashes; they must stay the uv.lock entries."""
    packages = {
        (package["name"], package["version"]): package
        for package in tomllib.loads((ROOT / "uv.lock").read_text())["package"]
    }
    text = (ROOT / ".clusterfuzzlite" / "requirements.txt").read_text()
    pins = re.findall(r"^([\w.-]+)==(\S+)((?:\s+\\\s+--hash=sha256:[0-9a-f]{64})+)", text, re.M)
    assert pins
    for name, version, hashes in pins:
        package = packages[(name, version)]
        locked = {package["sdist"]["hash"], *(wheel["hash"] for wheel in package["wheels"])}
        assert set(re.findall(r"sha256:[0-9a-f]{64}", hashes)) == locked, name
