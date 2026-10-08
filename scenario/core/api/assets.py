# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-free thumbnail downloads; generated results use jobs.transfers."""

import pathlib
import shutil
import time
import urllib.parse
import urllib.request

from .errors import NetworkError, ScenarioError
from .user_agent import user_agent_string


def _check_url(url):
    """Reject non-HTTPS, missing-host and malformed asset destinations before I/O."""
    try:
        parts = urllib.parse.urlsplit(url)
        valid = (
            isinstance(url, str)
            and not any(ord(char) <= 32 or ord(char) == 127 for char in url)
            and parts.scheme == "https"
            and bool(parts.hostname)
            and parts.username is None
            and parts.password is None
            and parts.port != 0
        )
    except (TypeError, ValueError, AttributeError):
        valid = False
    if not valid:
        raise ScenarioError(0, "refusing non-https asset URL") from None


def _safe_url(url):
    """Omit signed query strings and fragments from validated URL diagnostics."""
    return urllib.parse.urlsplit(url)._replace(query="", fragment="").geturl()


def download_file(url, dest, transport=None, timeout=300, retries=3, sleep=time.sleep):
    """Download a signed CDN URL to `dest` (atomic rename), streaming to disk, with bounded retries.

    Large 3D bundles (a Meshy OBJ is 200+ MB) have seen the CDN close the connection mid-transfer;
    one retry with a short backoff recovers it. The query string is never altered (it carries the signature)."""
    _check_url(url)
    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    delay = 1.0
    last_error = None
    for attempt in range(retries + 1):
        try:
            if transport is not None:
                status, _headers, raw = transport.request("GET", url, {}, None, timeout)
                if status >= 400:
                    raise ScenarioError(status, f"download failed ({status}) for {_safe_url(url)}")
                tmp.write_bytes(raw)
            else:
                req = urllib.request.Request(url, headers={"User-Agent": user_agent_string()})
                with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
                    shutil.copyfileobj(resp, out, 1024 * 1024)
            tmp.replace(dest)
            return dest
        except ScenarioError as err:
            if err.status and err.status < 500 and err.status not in (408, 429):
                raise
            last_error = err
        except (OSError, NetworkError) as err:  # includes URLError, RemoteDisconnected, timeouts
            last_error = err
        if attempt < retries:
            sleep(delay)
            delay *= 2
    raise NetworkError(0, f"download failed after {retries + 1} attempts: {last_error}")
