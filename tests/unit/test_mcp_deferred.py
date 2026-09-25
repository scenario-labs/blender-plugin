# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later


def test_deferred_tool_work_runs_between_main_thread_preparation_and_delivery():
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from scenario.mcp.protocol import DeferredTool, Registry, ToolSpec
    from scenario.mcp.server import McpServer

    entered, release = threading.Event(), threading.Event()
    phases = []
    main = threading.current_thread()

    def run():
        phases.append(("run", threading.current_thread()))
        entered.set()
        assert release.wait(5)
        return {"cu_cost_exact": "1.234567890123456789"}

    def finish(value):
        phases.append(("finish", threading.current_thread()))
        return value

    def prepare(args):
        phases.append(("prepare", threading.current_thread()))
        return DeferredTool(run, finish)

    registry = Registry()
    registry.add(ToolSpec("estimate", "Price", {}, prepare))
    server = McpServer("127.0.0.1", 0, "fixture-token", registry, {}, timeout=5)
    message = {"id": 1, "method": "tools/call", "params": {"name": "estimate"}}
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(server.handle, message)
        deadline = time.monotonic() + 5
        try:
            while not entered.is_set() and time.monotonic() < deadline:
                server.process_pending()
                entered.wait(0.001)
            assert entered.is_set()
            assert not result.done()
            assert server.process_pending() == 0  # Network work does not occupy Blender.
        finally:
            release.set()
        while not result.done() and time.monotonic() < deadline:
            server.process_pending()
            time.sleep(0.001)
        response = result.result(1)
    assert [phase for phase, _ in phases] == ["prepare", "run", "finish"]
    assert phases[0][1] is main and phases[2][1] is main
    assert phases[1][1] is not main
    assert "1.234567890123456789" in response["result"]["content"][0]["text"]
