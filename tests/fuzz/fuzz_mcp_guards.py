# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fuzz the local MCP request guards: ``host_allowed`` and ``origin_allowed``.

``host_allowed`` accepts exactly 127.0.0.1, localhost or [::1] in any letter case,
with an optional port from 1 to 65535, inside optional spaces and tabs. An accepted
Origin is an HTTP(S) loopback origin with nothing after the host and port, and a
browser-serialized origin passes only for a loopback host. A bare "?" or "#" after the
port is tolerated, since it names no query or fragment. Header values are Latin-1 text,
as ``http.server`` decodes them. Generated values are mostly valid with one hostile part, the boundary that matters.
"""

import re
import sys

from support import DataProvider, split

from scenario.mcp import server

PROVIDER = DataProvider
LOOPBACK = ("127.0.0.1", "localhost", "[::1]")
# (valid, hostile) choices for each part of a Host or Origin value.
HOSTS = (
    [*LOOPBACK, "LOCALHOST", "LocalHost", "lOcAlHoSt"],
    [
        "::1",
        "127.0.0.2",
        "127.1",
        "0.0.0.0",
        "localhost.",
        "127.0.0.1.",
        "[::ffff:127.0.0.1]",
        "[0:0:0:0:0:0:0:1]",
        "[::1",
        "example.com",
        "127.0.0.1.example.com",
        "localhost.example",
        "[::1].example",
        "evil.com@localhost",
        "localhost@evil.com",
        "localhost#@evil.com",
        "ｌocalhost",
        "localhoſt",
        "İ",
        "local\x00host",
        "",
    ],
)
PORTS = (
    ["", ":1", ":80", ":65535", ":080", ":00080"],
    [
        ":",
        ":0",
        ":65536",
        ":000080",
        ":-1",
        ":+80",
        ": 80",
        ":1e3",
        ":0x50",
        ":8080:80",
        ":١٢",
        ":\xb2",
        ":99999999999999999999",
    ],
)
HOST_PADDING = (["", " ", "\t", " \t "], ["\x0b", "\x0c", "\r", "\n", "\xa0", "\x85", "\x00"])
SCHEMES = (["http", "https", "HTTP", "hTTps"], ["ftp", "ws", "file", "javascript", "null", ""])
SEPARATORS = (["://"], [":", ":/", ":///", "//", "://user@", "://user:pw@", "://@", ":\\\\"])
SUFFIXES = ([""], ["/", "/path", "?q", "#f", "\\", "%2f", ";x", "@evil.com", ".evil.com"])
ORIGIN_PADDING = ([""], [" ", "\t", "\x00", "\x1f", "\xa0", "\r\n"])
_HOST = re.compile(r"(127\.0\.0\.1|localhost|\[::1\])(?::([0-9]{1,5}))?", re.ASCII | re.IGNORECASE)
_ORIGIN = re.compile(
    r"[\x00-\x1f]*https?://(?:127\.0\.0\.1|localhost|\[::1\])(?::[0-9]*)?\??#?",
    re.ASCII | re.IGNORECASE,
)


def expected_host(value):
    match = _HOST.fullmatch(value.strip(" \t"))
    return match is not None and (match[2] is None or 0 < int(match[2]) <= 65535)


def check_host(value):
    assert server.host_allowed(value) == expected_host(value), f"Host {value!r}"


def check_origin(value):
    if server.origin_allowed(value):
        # urlsplit drops leading C0 controls and reports a bare "?" or "#" as no query or
        # fragment; nothing else may precede or follow the loopback scheme, host and port.
        assert _ORIGIN.fullmatch(value), f"Origin {value!r} is not a loopback origin"


def text(fdp, limit=24):
    return fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, limit)).decode("latin-1")


def part(fdp, choices):
    """Usually a valid choice; otherwise a hostile one or arbitrary Latin-1 text."""
    valid, hostile = choices
    pick = fdp.ConsumeIntInRange(0, 7)
    if pick < 5:
        return fdp.PickValueInList(valid)
    return fdp.PickValueInList(hostile) if pick < 7 else text(fdp, 4)


def TestOneInput(data):
    mode, rest = split(data)
    fdp = PROVIDER(rest)
    mode %= 3
    if mode == 0:
        value = rest.decode("latin-1")
        check_host(value)
        check_origin(value)
        return
    if mode == 1:
        value = part(fdp, HOST_PADDING) + part(fdp, HOSTS) + part(fdp, PORTS)
        check_host(value + part(fdp, HOST_PADDING))
        assert not server.host_allowed(None) and not server.host_allowed(b"localhost")
        return
    host = part(fdp, HOSTS)
    if fdp.ConsumeBool():
        # A browser serializes an origin as scheme://host[:port] with a lowercase host.
        port = fdp.ConsumeIntInRange(0, 65535)
        if host in LOOPBACK or re.fullmatch(r"[a-z0-9.-]+", host):
            scheme = fdp.PickValueInList(["http", "https"])
            origin = f"{scheme}://{host}" + (f":{port}" if port else "")
            expected = host in LOOPBACK
            assert server.origin_allowed(origin) == expected, f"Origin {origin!r}"
        return
    origin = part(fdp, ORIGIN_PADDING) + part(fdp, SCHEMES) + part(fdp, SEPARATORS)
    origin += host + part(fdp, PORTS) + part(fdp, SUFFIXES) + part(fdp, ORIGIN_PADDING)
    check_origin(origin)
    assert server.origin_allowed(None) and not server.origin_allowed(b"http://localhost")


if __name__ == "__main__":
    import atheris

    PROVIDER = atheris.FuzzedDataProvider
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
