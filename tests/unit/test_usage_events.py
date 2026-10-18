# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in usage events: the relay allowlist mirror, install ID, queue and sender. No sockets."""

import json
import logging
import ssl
import threading
import time
import urllib.error

import pytest

from scenario.core.telemetry import relay, usage

ID = "0123456789abcdef0123456789abcdef"
CONTEXT = {"extension_version": "1.2.3", "blender_version": "5.0.1", "os": "macos", "arch": "arm64"}


class Sends:
    """A fake transport: records each payload, optionally failing or running a hook."""

    def __init__(self, fail=None, hook=None):
        self.payloads, self.calls, self.times = [], [], []
        self.fail, self.hook = fail, hook
        self.arrived = threading.Event()

    def __call__(self, url, payload, timeout):
        self.calls.append((url, timeout))
        self.times.append(time.monotonic())
        if self.hook is not None:
            self.hook(payload)
        if self.fail is not None:
            raise self.fail
        self.payloads.append(json.loads(json.dumps(payload)))
        self.arrived.set()
        return 202


class Switch:
    def __init__(self, value=True):
        self.value = value

    def __call__(self):
        return self.value


def recorder(send=None, *, enabled=None, online=None, clock=None, **options):
    return usage.UsageRecorder(
        ID,
        CONTEXT,
        enabled=enabled or Switch(),
        online_access=online or Switch(),
        send=send or Sends(),
        url="https://relay.invalid/events",
        clock=clock or (lambda: 1_800_000_000.0),
        **options,
    )


def operator(outcome="finished", **extra):
    return {"operator": "scenario.generate", "outcome": outcome, **extra}


def tool(**extra):
    return {"tool": "scene_summary", "outcome": "ok", "duration_ms": 12, **extra}


# -- allowlist ------------------------------------------------------------------
@pytest.mark.parametrize(
    ("name", "properties"),
    [
        ("extension_started", {}),
        ("operator_used", operator()),
        ("operator_used", operator("cancelled")),
        ("operator_used", operator("error")),
        ("operator_used", operator("error", error_type="RuntimeError")),
        ("operator_used", operator("error", error_type="_" + "x" * 63)),
        ("operator_used", {"operator": "scenario." + "a" * 64, "outcome": "finished"}),
        ("operator_used", {"operator": "scenario.a1_b2", "outcome": "finished"}),
        ("mcp_client_connected", {"client": "claude-code"}),
        ("mcp_client_connected", {"client": "Claude Desktop", "client_version": "0.14.1"}),
        ("mcp_client_connected", {"client": "a" * 64, "client_version": "1+build.2-rc_3"}),
        ("mcp_tool_called", tool()),
        ("mcp_tool_called", tool(outcome="error")),
        ("mcp_tool_called", tool(outcome="timeout", duration_ms=0)),
        ("mcp_tool_called", tool(duration_ms=3_600_000)),
        ("mcp_tool_called", tool(client="cursor-vscode")),
        ("mcp_tool_called", {"tool": "a" + "1" * 63, "outcome": "ok", "duration_ms": 1}),
    ],
)
def test_allowed_events_pass_unchanged(name, properties):
    assert usage.sanitize_event(name, properties) == properties


@pytest.mark.parametrize(
    ("name", "properties"),
    [
        ("extension_installed", {}),
        (None, {}),
        ("extension_started", None),
        ("extension_started", {"operator": "scenario.generate"}),
        ("operator_used", {"outcome": "finished"}),
        ("operator_used", {"operator": "scenario.generate"}),
        ("operator_used", operator(prompt="a castle")),
        ("operator_used", {"operator": "object.select_all", "outcome": "finished"}),
        ("operator_used", {"operator": "scenario.", "outcome": "finished"}),
        ("operator_used", {"operator": "scenario.Generate", "outcome": "finished"}),
        ("operator_used", {"operator": "scenario." + "a" * 65, "outcome": "finished"}),
        ("operator_used", {"operator": "scenario.generate\n", "outcome": "finished"}),
        ("operator_used", {"operator": "scenario.gen٣", "outcome": "finished"}),
        ("operator_used", {"operator": 7, "outcome": "finished"}),
        ("operator_used", operator("failed")),
        ("operator_used", operator("FINISHED")),
        ("operator_used", operator("finished", error_type="RuntimeError")),
        ("operator_used", operator("cancelled", error_type="RuntimeError")),
        ("operator_used", operator("error", error_type="1Error")),
        ("operator_used", operator("error", error_type="Error." + "x")),
        ("operator_used", operator("error", error_type="E" * 65)),
        ("operator_used", operator("error", error_type="Erreuré")),
        ("operator_used", operator("error", error_type=None)),
        ("mcp_client_connected", {}),
        ("mcp_client_connected", {"client": ""}),
        ("mcp_client_connected", {"client": "-claude"}),
        ("mcp_client_connected", {"client": " claude"}),
        ("mcp_client_connected", {"client": "a" * 65}),
        ("mcp_client_connected", {"client": "@scope/inspector"}),
        ("mcp_client_connected", {"client": "claude\n"}),
        ("mcp_client_connected", {"client": "claude", "client_version": "1.0 beta"}),
        ("mcp_client_connected", {"client": "claude", "client_version": "1" * 33}),
        ("mcp_client_connected", {"client": "claude", "client_version": ".1"}),
        ("mcp_client_connected", {"client": "claude", "version": "1"}),
        ("mcp_tool_called", {"outcome": "ok", "duration_ms": 1}),
        ("mcp_tool_called", tool(tool="Scene_summary")),
        ("mcp_tool_called", tool(tool="1scene")),
        ("mcp_tool_called", tool(tool="scene-summary")),
        ("mcp_tool_called", tool(tool="a" * 65)),
        ("mcp_tool_called", tool(outcome="finished")),
        ("mcp_tool_called", tool(duration_ms=-1)),
        ("mcp_tool_called", tool(duration_ms=3_600_001)),
        ("mcp_tool_called", tool(duration_ms=1.0)),
        ("mcp_tool_called", tool(duration_ms=True)),
        ("mcp_tool_called", tool(duration_ms="5")),
        ("mcp_tool_called", {"tool": "scene_summary", "outcome": "ok"}),
        ("mcp_tool_called", tool(client="")),
        ("mcp_tool_called", tool(client="a/b")),
        ("mcp_tool_called", tool(arguments={"text": "hi"})),
        ("mcp_tool_called", tool(client_version="1.0")),
    ],
)
def test_events_the_relay_would_drop_are_refused(name, properties):
    assert usage.sanitize_event(name, properties) is None


def test_allowlist_covers_exactly_the_contract_events():
    assert usage.EVENTS == (
        "extension_started",
        "operator_used",
        "mcp_client_connected",
        "mcp_tool_called",
    )


def test_operator_properties_leave_out_an_error_type_the_relay_refuses():
    assert usage.operator_properties("scenario.generate", "error", "ValueError") == operator(
        "error", error_type="ValueError"
    )
    assert usage.operator_properties("scenario.generate", "error", "Érreur") == operator("error")
    assert usage.operator_properties("scenario.generate", "error", "E" * 65) == operator("error")
    assert usage.operator_properties("scenario.generate", "finished", "ValueError") == operator()


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        (
            {"name": "claude-code", "version": "2.1.3"},
            {"client": "claude-code", "client_version": "2.1.3"},
        ),
        ({"name": "Claude Desktop"}, {"client": "Claude Desktop"}),
        (
            {"name": "@scope/inspector", "version": "0.1 (dev)"},
            {"client": "scope-inspector", "client_version": "0.1--dev"},
        ),
        (
            {"name": "x" * 100, "version": "9" * 40},
            {"client": "x" * 64, "client_version": "9" * 32},
        ),
        ({"name": "café", "version": "١.0"}, {"client": "caf", "client_version": "0"}),
        ({"name": "codex", "version": 3}, {"client": "codex"}),
        ({"name": "codex", "version": "---"}, {"client": "codex"}),
        ({"name": ""}, None),
        ({"name": "  --  "}, None),
        ({"name": 4}, None),
        ({"version": "1"}, None),
        (None, None),
        ("claude", None),
    ],
)
def test_client_info_is_fitted_to_the_relay_patterns(info, expected):
    properties = usage.client_properties(info)
    assert properties == expected
    if properties is not None:
        assert usage.sanitize_event("mcp_client_connected", properties) == properties


# -- context --------------------------------------------------------------------
@pytest.mark.parametrize(
    ("system", "machine", "os_name", "arch"),
    [
        ("Darwin", "arm64", "macos", "arm64"),
        ("Darwin", "x86_64", "macos", "x64"),
        ("Windows", "AMD64", "windows", "x64"),
        ("Windows", "ARM64", "windows", "arm64"),
        ("Linux", "x86_64", "linux", "x64"),
        ("Linux", "aarch64", "linux", "arm64"),
        ("FreeBSD", "riscv64", "other", "other"),
        ("", "", "other", "other"),
    ],
)
def test_context_maps_platform_names(system, machine, os_name, arch):
    assert relay.context("1.2.3", "5.0.1", system=system, machine=machine) == {
        "extension_version": "1.2.3",
        "blender_version": "5.0.1",
        "os": os_name,
        "arch": arch,
    }


def test_context_drops_invalid_and_unknown_fields():
    assert relay.context("1.2", "5.1.0 Alpha", system="Linux", machine="x86_64") == {
        "os": "linux",
        "arch": "x64",
    }
    assert relay.sanitize_context(
        {
            "extension_version": "５.0.1",
            "blender_version": "5.0.1\n",
            "os": "Darwin",
            "arch": "arm64",
            "hostname": "studio",
        }
    ) == {"arch": "arm64"}
    assert relay.sanitize_context(None) == {}
    assert relay.context("1.2.3", "5.0.1")["os"] in ("macos", "windows", "linux", "other")


# -- relay POST -----------------------------------------------------------------
class Response:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_post_json_sends_compact_json_with_the_extension_identity():
    seen = []

    def opener(request, timeout, context):
        seen.append((request, timeout, context))
        return Response()

    assert relay.post_json("https://relay.invalid/events", {"a": [1]}, opener=opener) == 202
    [(request, timeout, context)] = seen
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    assert request.get_method() == "POST" and timeout == relay.TIMEOUT == 5.0
    assert request.full_url == "https://relay.invalid/events"
    assert request.data == b'{"a":[1]}'
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("User-agent").startswith("ScenarioBlender/")


def test_post_json_refuses_a_body_the_relay_would_reject_and_raises_refusals():
    def opener(request, timeout, context):
        raise AssertionError("must not connect")

    with pytest.raises(ValueError):
        relay.post_json("https://relay.invalid/", {"text": "x" * relay.MAX_BODY}, opener=opener)

    def refused(request, timeout, context):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        relay.post_json("https://relay.invalid/", {}, opener=refused)


def test_a_full_batch_of_the_largest_events_fits_the_relay_body_limit():
    largest = {
        "event": "mcp_tool_called",
        "timestamp": usage.timestamp(1_800_000_000),
        "properties": {
            "tool": "a" * 64,
            "outcome": "timeout",
            "duration_ms": 3_600_000,
            "client": "c" * 64,
        },
    }
    payload = {"install_id": ID, "context": CONTEXT, "events": [largest] * usage.BATCH_LIMIT}
    assert len(json.dumps(payload, separators=(",", ":"))) < relay.MAX_BODY


# -- install ID -----------------------------------------------------------------
def test_install_id_lifecycle(tmp_path):
    directory = tmp_path / "state"
    assert usage.read_install_id(directory) is None
    first = usage.create_install_id(directory)
    assert usage.INSTALL_ID.fullmatch(first)
    assert usage.read_install_id(directory) == first
    assert (directory / usage.INSTALL_ID_FILE).read_text() == first + "\n"
    second = usage.create_install_id(directory)
    assert second != first and usage.read_install_id(directory) == second
    assert sorted(path.name for path in directory.iterdir()) == [usage.INSTALL_ID_FILE]
    usage.delete_install_id(directory)
    assert usage.read_install_id(directory) is None
    assert not (directory / usage.INSTALL_ID_FILE).exists()
    usage.delete_install_id(directory)  # already gone


@pytest.mark.parametrize("content", ["", "not-an-id", ID.upper(), ID[:-1], ID + "0", "\xff"])
def test_an_unusable_install_id_reads_as_missing(tmp_path, content):
    (tmp_path / usage.INSTALL_ID_FILE).write_bytes(content.encode("latin-1"))
    assert usage.read_install_id(tmp_path) is None


def test_recorder_refuses_an_invalid_install_id():
    with pytest.raises(ValueError):
        usage.UsageRecorder("x", {}, enabled=Switch(), online_access=Switch())
    with pytest.raises(TypeError):
        usage.UsageRecorder(ID, {}, enabled=True, online_access=Switch())


# -- queue ----------------------------------------------------------------------
def test_recorded_events_are_sent_in_the_relay_shape():
    sends = Sends()
    owner = recorder(sends)
    assert owner.record("extension_started")
    assert owner.record("operator_used", operator())
    assert owner.flush() == 2
    [payload] = sends.payloads
    assert payload == {
        "install_id": ID,
        "context": CONTEXT,
        "events": [
            {"event": "extension_started", "timestamp": "2027-01-15T08:00:00Z", "properties": {}},
            {
                "event": "operator_used",
                "timestamp": "2027-01-15T08:00:00Z",
                "properties": operator(),
            },
        ],
    }
    assert sends.calls == [("https://relay.invalid/events", relay.TIMEOUT)]
    assert owner.pending() == 0 and owner.flush() == 0 and len(sends.payloads) == 1


def test_the_posted_body_is_exactly_the_relay_shape_without_nulls():
    """install_id, context and events only; absent optional fields are omitted, never null."""
    seen = []

    def opener(request, timeout, context):
        seen.append(request)
        return Response()

    owner = usage.UsageRecorder(
        ID,
        {**CONTEXT, "arch": None, "hostname": "studio"},
        enabled=Switch(),
        online_access=Switch(),
        send=lambda url, payload, timeout: relay.post_json(url, payload, timeout, opener=opener),
        url="https://relay.invalid/events",
        clock=lambda: 1_800_000_000.0,
    )
    owner.record("operator_used", usage.operator_properties("scenario.generate", "error", None))
    owner.record(
        "mcp_client_connected", usage.client_properties({"name": "codex", "version": None})
    )
    owner.record("mcp_tool_called", tool())
    assert owner.flush() == 3
    [request] = seen
    assert request.data == (
        b'{"install_id":"0123456789abcdef0123456789abcdef",'
        b'"context":{"extension_version":"1.2.3","blender_version":"5.0.1","os":"macos"},'
        b'"events":['
        b'{"event":"operator_used","timestamp":"2027-01-15T08:00:00Z",'
        b'"properties":{"operator":"scenario.generate","outcome":"error"}},'
        b'{"event":"mcp_client_connected","timestamp":"2027-01-15T08:00:00Z",'
        b'"properties":{"client":"codex"}},'
        b'{"event":"mcp_tool_called","timestamp":"2027-01-15T08:00:00Z",'
        b'"properties":{"tool":"scene_summary","outcome":"ok","duration_ms":12}}]}'
    )
    assert b"null" not in request.data


def test_the_default_destination_is_the_relay_events_endpoint():
    assert usage.EVENTS_URL == "https://blender.scenario.com/telemetry/v1/events"
    owner = usage.UsageRecorder(ID, CONTEXT, enabled=Switch(), online_access=Switch())
    assert owner._url == usage.EVENTS_URL and owner._send is relay.post_json


def test_refused_events_never_enter_the_queue():
    owner = recorder()
    assert not owner.record("operator_used", operator(prompt="a castle"))
    assert not owner.record("scene_saved")
    assert owner.pending() == 0


def test_queue_is_bounded_and_drops_the_oldest():
    sends = Sends()
    clock = iter(range(1_800_000_000, 1_800_002_000)).__next__
    owner = recorder(sends, clock=lambda: float(clock()))
    for index in range(usage.QUEUE_LIMIT + 5):
        assert owner.record("mcp_tool_called", tool(duration_ms=index))
    assert owner.pending() == usage.QUEUE_LIMIT
    owner.flush()
    sent = [event["properties"]["duration_ms"] for p in sends.payloads for event in p["events"]]
    assert sent == list(range(5, usage.QUEUE_LIMIT + 5))
    assert [len(p["events"]) for p in sends.payloads] == [usage.BATCH_LIMIT] * 10


def test_batches_hold_at_most_one_hundred_events():
    sends = Sends()
    owner = recorder(sends)
    for _ in range(250):
        owner.record("extension_started")
    assert owner.flush() == 250
    assert [len(p["events"]) for p in sends.payloads] == [100, 100, 50]


@pytest.mark.parametrize("withdrawn", ["enabled", "online"])
def test_nothing_is_recorded_while_sharing_is_off_or_offline(withdrawn):
    switches = {"enabled": Switch(), "online": Switch()}
    switches[withdrawn].value = False
    sends = Sends()
    owner = recorder(sends, **switches)
    assert not owner.record("extension_started")
    assert owner.pending() == 0
    switches[withdrawn].value = True
    assert owner.record("extension_started") and owner.flush() == 1


@pytest.mark.parametrize("withdrawn", ["enabled", "online"])
def test_each_send_rechecks_both_permissions(withdrawn):
    switches = {"enabled": Switch(), "online": Switch()}

    def withdraw(payload):
        switches[withdrawn].value = False

    sends = Sends(hook=withdraw)
    owner = recorder(sends, **switches)
    for _ in range(150):
        owner.record("extension_started")
    assert owner.flush() == 100
    assert len(sends.calls) == 1
    assert owner.pending() == 0  # the rest is discarded, never sent later
    switches[withdrawn].value = True
    assert owner.flush() == 0 and len(sends.calls) == 1


def test_turning_sharing_off_stops_a_flush_already_in_progress():
    """Off then quickly on again shares the same permission: the old batches still stop."""
    owner = None

    def switch_off_then_on(payload):
        owner.stop(discard=True)  # the preference goes off; `enabled` stays True (on again)

    sends = Sends(hook=switch_off_then_on)
    owner = recorder(sends)
    for _ in range(150):
        owner.record("extension_started")
    owner.flush()
    assert len(sends.calls) == 1  # the batch on the wire when it went off, and no other
    assert not owner.permitted() and not owner.record("extension_started")


@pytest.mark.parametrize(
    "saved",
    [
        lambda: None,  # deleted: sharing went off, here or in another Blender
        lambda: "f" * 32,  # replaced by a new opt-in
        lambda: (_ for _ in ()).throw(OSError("unreadable")),
    ],
    ids=["deleted", "replaced", "unreadable"],
)
def test_a_batch_never_goes_out_under_an_id_that_is_no_longer_saved(saved):
    sends = Sends()
    owner = recorder(sends, saved_install_id=saved)
    owner.record("extension_started")
    assert owner.flush() == 0 and sends.calls == [] and owner.pending() == 0


def test_the_saved_id_is_checked_before_each_batch():
    current = [ID]

    def delete_after_first(payload):
        current[0] = None

    sends = Sends(hook=delete_after_first)
    owner = recorder(sends, saved_install_id=lambda: current[0])
    for _ in range(150):
        owner.record("extension_started")
    assert owner.flush() == 100
    assert len(sends.calls) == 1 and sends.payloads[0]["install_id"] == ID


def test_permission_withdrawn_after_recording_discards_the_queue():
    online = Switch()
    sends = Sends()
    owner = recorder(sends, online=online)
    owner.record("extension_started")
    online.value = False
    assert owner.flush() == 0 and sends.calls == [] and owner.pending() == 0


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("https://relay.invalid/events?token=x", 429, "Too Many", {}, None),
        urllib.error.URLError("https://relay.invalid/events unreachable"),
        TimeoutError("timed out"),
        ValueError("too large"),
    ],
)
def test_a_failed_batch_is_dropped_without_retry_or_details(failure, caplog):
    sends = Sends(fail=failure)
    owner = recorder(sends)
    for _ in range(150):
        owner.record("operator_used", operator())
    with caplog.at_level(logging.DEBUG, logger="scenario.usage"):
        assert owner.flush() == 0
    assert len(sends.calls) == 2  # each batch tried once
    assert owner.pending() == 0 and owner.flush() == 0 and len(sends.calls) == 2
    records = [r for r in caplog.records if r.name == "scenario.usage"]
    assert records and all(r.levelno == logging.DEBUG for r in records)
    assert "relay.invalid" not in caplog.text and "scenario.generate" not in caplog.text
    assert type(failure).__name__ in caplog.text


def test_events_older_than_the_relay_accepts_are_not_sent():
    now = [1_800_000_000.0]
    sends = Sends()
    owner = recorder(sends, clock=lambda: now[0])
    owner.record("operator_used", operator("cancelled"))
    now[0] += usage.MAX_AGE - 1
    owner.record("operator_used", operator())
    now[0] += 2
    assert owner.flush() == 1
    assert sends.payloads[0]["events"][0]["properties"] == operator()


def test_timestamps_are_utc_iso_8601_to_the_second():
    assert usage.timestamp(0) == "1970-01-01T00:00:00Z"
    assert usage.timestamp(1_800_000_000.75) == "2027-01-15T08:00:00Z"


# -- sender thread --------------------------------------------------------------
def wait_for(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.005)
    return True


def test_sender_flushes_once_fifty_events_are_queued():
    sends = Sends()
    owner = recorder(sends, interval=60.0, min_gap=0.0)
    owner.start()
    try:
        for _ in range(usage.FLUSH_SIZE - 1):
            owner.record("extension_started")
        assert not sends.arrived.wait(0.3)
        owner.record("extension_started")
        assert sends.arrived.wait(5)
        assert [len(p["events"]) for p in sends.payloads] == [usage.FLUSH_SIZE]
    finally:
        owner.stop(discard=True, wait=5)


def test_sender_flushes_on_its_interval():
    sends = Sends()
    owner = recorder(sends, interval=0.05)
    owner.start()
    try:
        owner.record("extension_started")
        assert sends.arrived.wait(5)
        assert len(sends.payloads[0]["events"]) == 1
    finally:
        owner.stop(discard=True, wait=5)


def test_sender_keeps_a_minimum_gap_between_bursts():
    sends = Sends()
    owner = recorder(sends, interval=60.0, min_gap=0.3)
    owner.start()
    try:
        for _ in range(usage.FLUSH_SIZE):
            owner.record("extension_started")
        assert wait_for(lambda: len(sends.payloads) == 1)
        for _ in range(usage.FLUSH_SIZE):
            owner.record("extension_started")
        assert wait_for(lambda: len(sends.payloads) == 2)
        assert sends.times[1] - sends.times[0] >= 0.29
    finally:
        owner.stop(discard=True, wait=5)


def test_stop_sends_what_is_queued_unless_discarded():
    kept = Sends()
    owner = recorder(kept, interval=60.0)
    owner.start()
    owner.record("extension_started")
    owner.stop(wait=5)
    assert len(kept.payloads) == 1
    assert not owner.record("extension_started")

    discarded = Sends()
    owner = recorder(discarded, interval=60.0)
    owner.start()
    owner.record("extension_started")
    owner.stop(discard=True, wait=5)
    assert discarded.calls == [] and owner.pending() == 0


def test_final_send_still_requires_permission():
    enabled = Switch()
    sends = Sends()
    owner = recorder(sends, enabled=enabled, interval=60.0)
    owner.start()
    owner.record("extension_started")
    enabled.value = False
    owner.stop(wait=5)
    assert sends.calls == []


def test_recording_is_thread_safe():
    sends = Sends()
    owner = recorder(sends, interval=60.0)

    def burst():
        for _ in range(100):
            owner.record("mcp_tool_called", tool())

    threads = [threading.Thread(target=burst) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert owner.pending() == 800
    assert owner.flush() == 800


# -- MCP observer ---------------------------------------------------------------
def test_mcp_observer_records_only_through_a_running_recorder():
    current = [None]
    observer = usage.McpObserver(lambda: current[0])
    observer.client_connected({"name": "claude-code"})
    observer.tool_called("scene_summary", "ok", 5)
    sends = Sends()
    current[0] = recorder(sends)
    observer.client_connected({"name": "claude-code", "version": "2.0"})
    observer.client_connected({"name": ""})
    observer.tool_called("scene_summary", "timeout", 9_999_999)
    observer.tool_called("scene_summary", "ok", -3)
    observer.tool_called("Not A Tool", "ok", 1)
    current[0].flush()
    assert [(e["event"], e["properties"]) for e in sends.payloads[0]["events"]] == [
        ("mcp_client_connected", {"client": "claude-code", "client_version": "2.0"}),
        ("mcp_tool_called", tool(outcome="timeout", duration_ms=usage.MAX_DURATION_MS)),
        ("mcp_tool_called", tool(duration_ms=0)),
    ]
