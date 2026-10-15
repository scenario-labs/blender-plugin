# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fuzz the local MCP JSON-RPC layer: ``parse_body``, then ``handle_message`` per message.

A body either fails with one parse error or, per message, gets no reply for a
notification and otherwise one well-formed JSON-RPC 2.0 reply with a documented
error code. Only the registered tool a request names runs. With an executor,
handlers and deferred finishes run through it unless the tool is off-thread, and
deferred work runs outside it. A timeout is a TOOL_TIMEOUT error, and a failure
naming a local file never returns that path.
"""

import json
import sys

from support import DataProvider, json_value, mostly, split

from scenario.mcp import protocol

PROVIDER = DataProvider
SERVER_INFO = {"name": "fuzz", "version": "0"}
SECRET = "/private/fuzz-secret-path"
CODES = {
    protocol.PARSE_ERROR,
    protocol.INVALID_REQUEST,
    protocol.METHOD_NOT_FOUND,
    protocol.INVALID_PARAMS,
    protocol.INTERNAL_ERROR,
    protocol.TOOL_TIMEOUT,
}
METHODS = ["initialize", "ping", "tools/list", "tools/call", "notifications/initialized", "x"]
NAMES = ["echo", "needs", "fails", "leaks", "slow", "deferred", "offthread"]
WORDS = [*NAMES, "a", "b", "depth"]


class Run:
    """One input's tools, executor and the calls they record."""

    def __init__(self, fdp):
        self.calls = []
        self.in_executor = False
        self.executor_calls = 0
        # The executor call that times out, as the main-thread queue would; 0 never does.
        self.timeout_at = fdp.ConsumeIntInRange(0, 4)
        self.registry = protocol.Registry()
        schema = {"type": "object"}
        for name, handler in (
            ("echo", lambda arguments: arguments),
            ("fails", self._fails),
            ("leaks", self._leaks),
            ("slow", self._slow),
            ("deferred", self._deferred),
        ):
            self.registry.add(protocol.ToolSpec(name, name, schema, self._recorded(name, handler)))
        self.registry.add(
            protocol.ToolSpec(
                "needs",
                "needs",
                {"type": "object", "required": ["a", "b"]},
                self._recorded("needs", lambda arguments: "ok"),
            )
        )
        self.registry.add(
            protocol.ToolSpec(
                "offthread",
                "offthread",
                schema,
                self._recorded("offthread", lambda arguments: {"_image": "AAAA"}),
                offthread=True,
            )
        )

    def executor(self, handler, arguments):
        self.executor_calls += 1
        if self.executor_calls == self.timeout_at:
            raise protocol.ToolTimeout("queued too long")
        self.in_executor = True
        try:
            return handler(arguments)
        finally:
            self.in_executor = False

    def _recorded(self, name, handler):
        def call(arguments):
            self.calls.append((name, "call", self.in_executor))
            return handler(arguments)

        return call

    @staticmethod
    def _fails(arguments):
        raise ValueError("refused")

    @staticmethod
    def _leaks(arguments):
        raise OSError(2, "No such file or directory", SECRET)

    @staticmethod
    def _slow(arguments):
        raise protocol.ToolTimeout("slow")

    def _deferred(self, arguments):
        depth = arguments.get("depth")
        return self._step(depth if type(depth) is int and 1 <= depth <= 3 else 1)

    def _step(self, depth):
        def work():
            self.calls.append(("deferred", "run", self.in_executor))
            return depth

        def finish(completed):
            self.calls.append(("deferred", "finish", self.in_executor))
            return self._step(depth - 1) if depth > 1 else {"done": completed}

        return protocol.DeferredTool(work, finish)


def message(fdp):
    item = {"jsonrpc": mostly(fdp, ["2.0"], ["1.0", 2, None])}
    if fdp.ConsumeIntInRange(0, 7):
        item["id"] = mostly(fdp, [1, "a", 0, 2**70], [None, True, 1.5], WORDS)
    if fdp.ConsumeIntInRange(0, 15):
        item["method"] = mostly(fdp, ["tools/call"] * 3 + METHODS, (), WORDS)
    if fdp.ConsumeIntInRange(0, 7):
        params = {}
        if fdp.ConsumeIntInRange(0, 7):
            params["name"] = mostly(fdp, NAMES, ["", "x", "ECHO"], WORDS)
        if fdp.ConsumeIntInRange(0, 3):
            arguments = {
                key: json_value(fdp, WORDS, 1) for key in ("a", "b", "depth") if fdp.ConsumeBool()
            }
            params["arguments"] = mostly(fdp, [arguments], (), WORDS)
        if fdp.ConsumeBool():
            params["protocolVersion"] = mostly(fdp, protocol.PROTOCOL_VERSIONS, ["1"], WORDS)
        item["params"] = mostly(fdp, [params], (), WORDS)
    return mostly(fdp, [item], (), WORDS)


def body(mode, fdp, rest):
    if mode % 3 == 0:
        return rest
    if mode % 3 == 1:
        value = message(fdp)
    else:
        value = [message(fdp) for _ in range(fdp.ConsumeIntInRange(0, 4))]
    return json.dumps(value, ensure_ascii=fdp.ConsumeBool()).encode("utf-8")


def check_reply(item, response, run, spec, executor):
    if isinstance(item, dict) and "method" in item and item.get("id") is None:
        assert response is None, "a notification gets no reply"
        assert not run.calls, "a notification runs no tool"
        return
    assert isinstance(response, dict), "every request gets one reply"
    assert set(response) in ({"jsonrpc", "id", "result"}, {"jsonrpc", "id", "error"})
    assert response["jsonrpc"] == "2.0"
    expected = item.get("id") if isinstance(item, dict) else None
    assert response["id"] is expected or response["id"] == expected, "the reply echoes the id"
    json.dumps(response)
    error = response.get("error")
    if error is not None:
        assert set(error) <= {"code", "message", "data"}
        assert type(error["code"]) is int and error["code"] in CODES
        assert isinstance(error["message"], str)
    if not isinstance(item, dict) or "method" not in item:
        assert error is not None and error["code"] == protocol.INVALID_REQUEST
        return
    method, params = item["method"], item.get("params")
    params = {} if params is None else params  # Only an omitted or null value is empty.
    if not isinstance(params, dict):
        assert error is not None and error["code"] in {
            protocol.INVALID_PARAMS,
            protocol.METHOD_NOT_FOUND,
        }, "parameters that are not an object are refused"
        assert not run.calls
        return
    if method == "initialize":
        assert response["result"]["protocolVersion"] in protocol.PROTOCOL_VERSIONS
        assert response["result"]["serverInfo"] == SERVER_INFO
    elif method == "ping":
        assert response["result"] == {}
    elif method == "tools/list":
        names = [tool["name"] for tool in response["result"]["tools"]]
        assert names == run.registry.names()
    elif method == "tools/call":
        check_call(params, response, run, spec, executor)
        return
    else:
        assert error is not None and error["code"] == protocol.METHOD_NOT_FOUND
    assert not run.calls, "only tools/call runs a tool"


def check_call(params, response, run, spec, executor):
    if spec is None:
        assert response["error"]["code"] == protocol.INVALID_PARAMS
        assert not run.calls, "an unregistered tool never runs"
        return
    assert {name for name, _, _ in run.calls} <= {spec.name}, "only the named tool runs"
    arguments = params.get("arguments") or {}
    required = spec.input_schema.get("required", ())
    if not isinstance(arguments, dict) or any(name not in arguments for name in required):
        assert not run.calls, "a call without its required arguments never runs"
    for _, phase, on_executor in run.calls:
        expected = executor is not None and phase != "run" and not spec.offthread
        assert on_executor == expected, f"{phase} ran on the wrong thread"
    if "error" in response:
        assert response["error"]["code"] == protocol.TOOL_TIMEOUT
        assert spec.name == "slow" or (
            executor is not None and run.executor_calls == run.timeout_at
        )
        return
    content = response["result"]["content"]
    assert isinstance(content, list) and all("type" in part for part in content)
    if response["result"].get("isError"):
        assert all(SECRET not in part.get("text", "") for part in content), "a path leaked"
    else:
        assert spec.name in {"echo", "needs", "deferred", "offthread"}


def TestOneInput(data):
    mode, rest = split(data)
    fdp = PROVIDER(rest)
    raw = body(mode, fdp, rest)
    use_executor = fdp.ConsumeBool()
    parsed, parse_error = protocol.parse_body(raw)
    if parse_error is not None:
        assert parsed is None
        assert parse_error["id"] is None
        assert parse_error["error"]["code"] == protocol.PARSE_ERROR
        return
    previous = protocol.log.disabled
    protocol.log.disabled = True
    try:
        for item in parsed if isinstance(parsed, list) else [parsed]:
            run = Run(fdp)
            executor = run.executor if use_executor else None
            response = protocol.handle_message(item, run.registry, SERVER_INFO, executor)
            params = item.get("params") if isinstance(item, dict) else None
            name = params.get("name") if isinstance(params, dict) else None
            spec = run.registry.get(name) if isinstance(name, str) else None
            check_reply(item, response, run, spec, executor)
    finally:
        protocol.log.disabled = previous


if __name__ == "__main__":
    import atheris

    PROVIDER = atheris.FuzzedDataProvider
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
