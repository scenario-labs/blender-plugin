# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
# OSS-Fuzz Python builder: Python 3.11.13, Atheris 3.0.0 and PyInstaller 6.10.0 at this digest.
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:0aa4f12ee4e9a4aaa1e511b3ded82d662475150b82a786478f22d5c41adbacbd
COPY .clusterfuzzlite/requirements.txt /tmp/fuzz-requirements.txt
RUN python3 -m pip install --no-cache-dir --no-deps --only-binary=:all: --require-hashes \
    -r /tmp/fuzz-requirements.txt
COPY . $SRC/blender-plugin
WORKDIR $SRC/blender-plugin
COPY .clusterfuzzlite/build.sh $SRC/
