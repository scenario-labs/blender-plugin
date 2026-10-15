#!/bin/bash -eu
# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
# Compile every Atheris harness with its seed corpus; nothing here needs Blender.
cd "$SRC/blender-plugin"
python3 tests/fuzz/samples.py "$OUT"
for fuzzer in tests/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$fuzzer" --paths "$SRC/blender-plugin"
done
