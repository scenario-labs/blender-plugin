# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import logging
import os

import pytest

from scenario.core.api.errors import ScenarioError
from scenario.core.jobs.coordinator import QuoteError
from scenario.core.jobs.store import StoreError
from scenario.mcp import protocol

INFO = {"name": "scenario-blender", "version": "0.4.0"}


def _raise(err):
    raise err


def registry():
    reg = protocol.Registry()
    reg.add(
        protocol.ToolSpec(
            "echo",
            "Echo arguments",
            {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
            lambda args: {"echo": args["text"]},
        )
    )
    reg.add(
        protocol.ToolSpec(
            "boom",
            "Always fails",
            {"type": "object", "properties": {}},
            lambda args: _raise(RuntimeError("kaput")),
        )
    )
    reg.add(
        protocol.ToolSpec(
            "shot",
            "Image",
            {"type": "object", "properties": {}},
            lambda args: {"_image": "aGk=", "mimeType": "image/png"},
        )
    )
    return reg


def test_initialize_echoes_supported_version_and_lists_tools_capability():
    resp = protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "1"},
            },
        },
        registry(),
        INFO,
    )
    assert resp["id"] == 1 and resp["result"]["protocolVersion"] == "2025-03-26"
    assert resp["result"]["serverInfo"] == INFO and "tools" in resp["result"]["capabilities"]
    newer = protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {"protocolVersion": "2099-01-01"},
        },
        registry(),
        INFO,
    )
    assert newer["result"]["protocolVersion"] == protocol.PROTOCOL_VERSIONS[0]


def test_notifications_return_none_and_ping_returns_empty_result():
    assert (
        protocol.handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}, registry(), INFO
        )
        is None
    )
    assert (
        protocol.handle_message({"jsonrpc": "2.0", "id": 3, "method": "ping"}, registry(), INFO)[
            "result"
        ]
        == {}
    )


def test_tools_list_and_call_text_result():
    reg = registry()
    listed = protocol.handle_message(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/list"}, reg, INFO
    )["result"]["tools"]
    assert [t["name"] for t in listed] == ["echo", "boom", "shot"] and listed[0]["inputSchema"][
        "required"
    ] == ["text"]
    called = protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "hi"}},
        },
        reg,
        INFO,
    )
    content = called["result"]["content"]
    assert content[0]["type"] == "text" and json.loads(content[0]["text"]) == {"echo": "hi"}
    assert called["result"].get("isError") is not True


def test_tool_errors_and_unknown_tools():
    reg = registry()
    failed = protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "boom", "arguments": {}},
        },
        reg,
        INFO,
    )
    assert failed["result"]["isError"] is True
    assert failed["result"]["content"][0]["text"] == (
        "RuntimeError: boom failed unexpectedly; see the Blender console"
    )
    unknown = protocol.handle_message(
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "nope"}}, reg, INFO
    )
    assert unknown["error"]["code"] == -32602
    missing = protocol.handle_message({"jsonrpc": "2.0", "id": 8, "method": "no/such"}, reg, INFO)
    assert missing["error"]["code"] == -32601
    bad = protocol.handle_message({"id": 9}, reg, INFO)
    assert bad["error"]["code"] == -32600


def test_image_results_and_executor_hook():
    reg = registry()
    shot = protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "shot", "arguments": {}},
        },
        reg,
        INFO,
    )
    assert shot["result"]["content"][0] == {
        "type": "image",
        "data": "aGk=",
        "mimeType": "image/png",
    }
    seen = []

    def executor(handler, arguments):
        seen.append(arguments)
        return handler(arguments)

    protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "x"}},
        },
        reg,
        INFO,
        executor=executor,
    )
    assert seen == [{"text": "x"}]


def test_timeout_error_from_executor():
    def executor(handler, arguments):
        raise protocol.ToolTimeout("main thread busy")

    resp = protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "x"}},
        },
        registry(),
        INFO,
        executor=executor,
    )
    assert resp["error"]["code"] == -32000 and "busy" in resp["error"]["message"]


def test_parse_body_errors():
    message, err = protocol.parse_body(b"{not json")
    assert message is None and err["error"]["code"] == -32700
    assert protocol.parse_body(b'{"jsonrpc":"2.0","id":1,"method":"ping"}')[0]["method"] == "ping"


PRIVATE_PATH = "/fixture-home/blender-profile/extensions/user_default/scenario/private.png"
INSTALLED_DIR = os.path.dirname(os.path.dirname(protocol.__file__))
UNEXPECTED = "fail failed unexpectedly; see the Blender console"

# Compiled into a module inside the extension package, as installed tool modules and the code
# they call are; the test module itself stands for bpy, the OS and libraries.
EXTENSION_SOURCE = """
def refuse(args):
    raise PermissionError("Python execution is disabled in Scenario preferences")

def reject(args):
    raise ValueError(
        "lane must be one of "
        "('image', 'video')"
    )

def unavailable(args):
    raise RuntimeError("The model catalog is still loading; call again in a few seconds")

def interrupted(args):
    error = RuntimeError("Tool execution was interrupted")
    raise error

def wrapped(args):
    try:
        open(args["path"])
    except OSError:
        raise RuntimeError("Could not read the capture; inspect it again") from None

def open_file(args):
    open(args["path"])

def parse(args):
    return int(args["path"])

def lookup(args):
    return {}[args["path"]]

def reraise(args):
    try:
        open(args["path"])
    except OSError:
        raise

def reraise_named(args):
    try:
        open(args["path"])
    except OSError as error:
        raise error

def name_file(args):
    raise PermissionError(13, "Permission denied", args["path"])
"""
EXTENSION = {"__name__": protocol.__name__.rsplit(".", 1)[0] + ".fixture_handlers"}
exec(compile(EXTENSION_SOURCE, "<extension-fixture>", "exec"), EXTENSION)


class LibraryValueError(ValueError):
    """A dependency's ValueError subclass, whose message the extension did not write."""


def _call(handler, *, executor=None):
    reg = protocol.Registry()
    reg.add(protocol.ToolSpec("fail", "Fails", {"type": "object"}, handler))
    response = protocol.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {"name": "fail", "arguments": {"path": PRIVATE_PATH}},
        },
        reg,
        INFO,
        executor=executor,
    )
    assert response["result"]["isError"] is True
    [content] = response["result"]["content"]
    assert content["type"] == "text"
    text = content["text"]
    assert "Traceback" not in text and 'File "' not in text and "\n" not in text
    assert INSTALLED_DIR not in text and PRIVATE_PATH not in text
    return text


def _logged(caplog, level):
    [record] = [r for r in caplog.records if r.name == "scenario.mcp"]
    assert record.levelno == level and record.exc_info is not None
    assert "Traceback" in caplog.text
    return record


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("refuse", "PermissionError: Python execution is disabled in Scenario preferences"),
        ("reject", "ValueError: lane must be one of ('image', 'video')"),
        (
            "unavailable",
            "RuntimeError: The model catalog is still loading; call again in a few seconds",
        ),
        ("interrupted", "RuntimeError: Tool execution was interrupted"),
        ("wrapped", "RuntimeError: Could not read the capture; inspect it again"),
    ],
)
def test_messages_raised_by_extension_code_are_returned_without_traceback(name, expected, caplog):
    caplog.set_level(logging.DEBUG, logger="scenario.mcp")
    assert _call(EXTENSION[name]) == expected
    _logged(caplog, logging.DEBUG)


@pytest.mark.parametrize(
    "error",
    [
        ScenarioError(0, "The estimate context changed; estimate again"),
        QuoteError("The quote no longer matches the request"),
        StoreError("Could not initialize job storage"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_extension_error_classes_keep_their_message_wherever_raised(error, caplog):
    caplog.set_level(logging.DEBUG, logger="scenario.mcp")
    assert _call(lambda args: _raise(error)) == f"{type(error).__name__}: {error}"
    assert _logged(caplog, logging.DEBUG).exc_info[1] is error


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("open_file", "FileNotFoundError"),
        ("parse", "ValueError"),
        ("lookup", "KeyError"),
        ("reraise", "FileNotFoundError"),
        ("reraise_named", "FileNotFoundError"),
        ("name_file", "PermissionError"),
    ],
)
def test_failures_from_calls_in_extension_code_return_fixed_text(name, kind, caplog):
    caplog.set_level(logging.DEBUG, logger="scenario.mcp")
    assert _call(EXTENSION[name]) == f"{kind}: {UNEXPECTED}"
    _logged(caplog, logging.ERROR)
    assert PRIVATE_PATH in caplog.text


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(2, "No such file or directory", PRIVATE_PATH),
        OSError(f"cannot write {PRIVATE_PATH}"),
        RuntimeError(f"Error: Cannot read '{PRIVATE_PATH}'"),
        ValueError(f"invalid literal {PRIVATE_PATH!r}"),
        LibraryValueError(f"invalid response field at {PRIVATE_PATH}"),
        TypeError(f"unsupported value {PRIVATE_PATH}"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_failures_raised_outside_the_extension_return_fixed_text(error, caplog):
    caplog.set_level(logging.DEBUG, logger="scenario.mcp")
    assert _call(lambda args: _raise(error)) == f"{type(error).__name__}: {UNEXPECTED}"
    assert _logged(caplog, logging.ERROR).exc_info[1] is error
    assert PRIVATE_PATH in caplog.text


def test_executor_and_deferred_failures_use_the_same_rule():
    def executor(handler, arguments):
        return handler(arguments)

    assert _call(EXTENSION["open_file"], executor=executor) == f"FileNotFoundError: {UNEXPECTED}"
    assert _call(EXTENSION["refuse"], executor=executor).startswith("PermissionError: Python")

    def deferred(finish):
        return lambda args: protocol.DeferredTool(run=lambda: {"path": PRIVATE_PATH}, finish=finish)

    assert _call(deferred(EXTENSION["lookup"])) == f"KeyError: {UNEXPECTED}"
    assert _call(deferred(EXTENSION["reject"])).startswith("ValueError: lane must be")
