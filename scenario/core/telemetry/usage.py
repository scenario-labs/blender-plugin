# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in anonymous usage events: allowlist, install ID, bounded queue and sender. No bpy.

The extension records four events, each with the properties the relay's allowlist names
and nothing else; sanitize_event mirrors that allowlist so an event the relay would drop
never enters the queue. Events wait in memory, at most QUEUE_LIMIT with the oldest dropped
first, until the sender thread posts them: every FLUSH_INTERVAL seconds, or sooner once
FLUSH_SIZE are queued, in batches of at most BATCH_LIMIT. Before each send it rereads two
worker-safe permissions, sharing enabled and online access, that only Blender's main
thread changes, and checks that its install ID is still the saved one. A failed batch is
dropped, never retried, and logged without its URL or contents. The install ID is random, stored under the extension's user directory, and not
derived from or linked to the Scenario account, key, team or project.
"""

import collections
import logging
import math
import os
import pathlib
import re
import threading
import time
import uuid

from . import relay

log = logging.getLogger("scenario.usage")

EVENTS_URL = relay.BASE_URL + "/events"
INSTALL_ID_FILE = "usage-install-id"
QUEUE_LIMIT = 1000
FLUSH_INTERVAL = 60.0
FLUSH_SIZE = 50
BATCH_LIMIT = 100
# A burst never posts more often than this, well inside the relay's 60 requests a minute.
MIN_SEND_GAP = 5.0
# The relay drops an event older than seven days.
MAX_AGE = 7 * 24 * 3600.0
MAX_DURATION_MS = 3_600_000

INSTALL_ID = re.compile(r"[0-9a-f]{32}")
OPERATOR = re.compile(r"scenario\.[a-z0-9_]{1,64}")
ERROR_TYPE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
MCP_CLIENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,63}")
MCP_CLIENT_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,31}")
MCP_TOOL = re.compile(r"[a-z][a-z0-9_]{0,63}")
OPERATOR_OUTCOMES = ("finished", "cancelled", "error")
TOOL_OUTCOMES = ("ok", "error", "timeout")
EVENTS = ("extension_started", "operator_used", "mcp_client_connected", "mcp_tool_called")


def _matches(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _only(properties, keys):
    return all(key in keys for key in properties)


def sanitize_event(name, properties):
    """The event's properties as the relay accepts them, or None when it would drop the event.

    Any property outside the event's list, or a value outside its pattern or range, drops
    the whole event, as the relay does. Patterns are ASCII and match the whole value.
    """
    if not isinstance(properties, dict):
        return None
    p = properties
    if name == "extension_started":
        return {} if not p else None
    if name == "operator_used":
        if not _only(p, ("operator", "outcome", "error_type")) or not _matches(
            p.get("operator"), OPERATOR
        ):
            return None
        if p.get("outcome") not in OPERATOR_OUTCOMES:
            return None
        if "error_type" in p and (
            p["outcome"] != "error" or not _matches(p["error_type"], ERROR_TYPE)
        ):
            return None
        return dict(p)
    if name == "mcp_client_connected":
        if not _only(p, ("client", "client_version")) or not _matches(p.get("client"), MCP_CLIENT):
            return None
        if "client_version" in p and not _matches(p["client_version"], MCP_CLIENT_VERSION):
            return None
        return dict(p)
    if name == "mcp_tool_called":
        if not _only(p, ("tool", "outcome", "duration_ms", "client")):
            return None
        duration = p.get("duration_ms")
        if (
            not _matches(p.get("tool"), MCP_TOOL)
            or p.get("outcome") not in TOOL_OUTCOMES
            or type(duration) is not int  # bool is an int too, and the relay refuses it
            or not 0 <= duration <= MAX_DURATION_MS
        ):
            return None
        if "client" in p and not _matches(p["client"], MCP_CLIENT):
            return None
        return dict(p)
    return None


def operator_properties(operator, outcome, error_type=None):
    """operator_used properties; an exception class name the relay would refuse is left out."""
    properties = {"operator": operator, "outcome": outcome}
    if outcome == "error" and _matches(error_type, ERROR_TYPE):
        properties["error_type"] = error_type
    return properties


def _label(value, pattern, limit):
    """A client's self-reported name or version made to fit its pattern, or None."""
    if not isinstance(value, str):
        return None
    allowed = " ._-" if pattern is MCP_CLIENT else "._+-"
    text = "".join(c if c.isascii() and (c.isalnum() or c in allowed) else "-" for c in value)
    text = text.strip(" ._+-")[:limit].rstrip(" ")
    return text if pattern.fullmatch(text) else None


def client_properties(client_info):
    """mcp_client_connected properties from an MCP initialize clientInfo, or None.

    Clients name themselves freely; characters outside the relay's pattern become hyphens,
    the name is cut to 64 characters and the version to 32. A version that still does not
    fit is left out; a client without a usable name is not reported.
    """
    if not isinstance(client_info, dict):
        return None
    client = _label(client_info.get("name"), MCP_CLIENT, 64)
    if client is None:
        return None
    properties = {"client": client}
    version = _label(client_info.get("version"), MCP_CLIENT_VERSION, 32)
    if version is not None:
        properties["client_version"] = version
    return properties


def timestamp(seconds):
    """ISO 8601 UTC with a Z, to the second, as the relay's example shows."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


# -- install ID ---------------------------------------------------------------
def read_install_id(directory):
    """The saved install ID, or None when it is missing or not a 32-hex-digit ID."""
    try:
        value = (pathlib.Path(directory) / INSTALL_ID_FILE).read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return None
    return value if INSTALL_ID.fullmatch(value) else None


def create_install_id(directory):
    """Save a new random install ID, replacing any previous one, and return it."""
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    value = uuid.uuid4().hex
    temporary = directory / f".{INSTALL_ID_FILE}.{os.getpid()}.tmp"
    temporary.write_text(value + "\n", encoding="ascii")
    temporary.replace(directory / INSTALL_ID_FILE)
    return value


def delete_install_id(directory):
    """Forget the install ID; a later opt-in starts with a new one."""
    (pathlib.Path(directory) / INSTALL_ID_FILE).unlink(missing_ok=True)


# -- queue and sender ---------------------------------------------------------
class UsageRecorder:
    """Thread-safe bounded queue of sanitized events and the thread that posts them.

    `enabled` and `online_access` are worker-safe callables, rechecked when an event is
    recorded and before every send. `saved_install_id` returns the ID saved now, or None;
    a batch goes out only while it is still this recorder's ID, so turning sharing off,
    here or in another Blender, stops even a batch already taken off the queue.
    `send(url, payload, timeout)` defaults to relay.post_json; tests replace it, the
    clocks and the URL.
    """

    def __init__(
        self,
        install_id,
        context,
        *,
        enabled,
        online_access,
        saved_install_id=None,
        send=None,
        url=EVENTS_URL,
        clock=time.time,
        monotonic=time.monotonic,
        interval=FLUSH_INTERVAL,
        min_gap=MIN_SEND_GAP,
        timeout=relay.TIMEOUT,
    ):
        if not INSTALL_ID.fullmatch(install_id or ""):
            raise ValueError("install_id must be 32 lowercase hexadecimal digits")
        if not callable(enabled) or not callable(online_access):
            raise TypeError("enabled and online_access must be callables")
        self.install_id = install_id
        self.context = relay.sanitize_context(context)
        self._enabled, self._online_access = enabled, online_access
        self._saved_install_id = saved_install_id
        self._send = send or relay.post_json
        self._url, self._timeout = url, timeout
        self._clock, self._monotonic = clock, monotonic
        self._interval, self._min_gap = interval, min_gap
        self._queue = collections.deque(maxlen=QUEUE_LIMIT)  # (seconds, event), oldest first
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._discarded = threading.Event()  # never cleared: a stopped recorder is not reused
        self._in_flight = threading.Event()  # events taken off the queue and not yet settled
        self._last_send = -math.inf
        self._thread = None

    def permitted(self):
        return bool(not self._discarded.is_set() and self._enabled() and self._online_access())

    def _sendable(self):
        """permitted(), and the install ID this recorder sends under is still the saved one."""
        if not self.permitted():
            return False
        if self._saved_install_id is None:
            return True
        try:
            return self._saved_install_id() == self.install_id
        except Exception:  # an unreadable ID is no opt-in
            return False

    def pending(self):
        with self._lock:
            return len(self._queue)

    def busy(self):
        """Events are queued, or taken off the queue by a send that has not finished."""
        with self._lock:
            return bool(self._queue) or self._in_flight.is_set()

    def record(self, name, properties=None):
        """Queue one event; returns False when it is refused, sharing is off or offline."""
        if self._stopping.is_set() or not self.permitted():
            return False
        clean = sanitize_event(name, {} if properties is None else properties)
        if clean is None:
            log.debug("Usage event refused by the allowlist")
            return False
        at = self._clock()
        event = {"event": name, "timestamp": timestamp(at), "properties": clean}
        with self._lock:
            self._queue.append((at, event))
            full = len(self._queue) >= FLUSH_SIZE
        if full:
            self._wake.set()
        return True

    def clear(self):
        with self._lock:
            self._queue.clear()

    def flush(self):
        """Send everything queued now, in batches; returns how many events were accepted.

        Events are taken off the queue first: whatever fails is dropped, not requeued.
        """
        with self._lock:
            queued = list(self._queue)
            self._queue.clear()
            if queued:
                self._in_flight.set()  # under the lock: busy() never sees a gap
        try:
            return self._send_batches(queued)
        finally:
            self._in_flight.clear()

    def _send_batches(self, queued):
        oldest = self._clock() - MAX_AGE
        events = [event for at, event in queued if at >= oldest]
        sent = 0
        for start in range(0, len(events), BATCH_LIMIT):
            if not self._sendable():
                log.debug("Usage events discarded: sharing is off or online access is disabled")
                break
            batch = events[start : start + BATCH_LIMIT]
            payload = {"install_id": self.install_id, "context": self.context, "events": batch}
            self._last_send = self._monotonic()
            try:
                self._send(self._url, payload, self._timeout)
            except Exception as error:  # dropped: no retry loop, no URL or payload in the log
                log.debug("Usage batch dropped: %s", type(error).__name__)
                continue
            sent += len(batch)
        return sent

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True, name="scenario-usage")
            self._thread.start()

    def stop(self, *, discard=False, wait=None):
        """End the sender. Without discard it sends what is queued first, if still permitted.

        Blender's main thread calls this: it waits for that last send only up to `wait`
        seconds, and not at all by default.
        """
        if discard:
            self._discarded.set()
            self.clear()
        self._stopping.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and wait:
            thread.join(wait)

    def _run(self):
        due = self._monotonic() + self._interval
        while not self._stopping.is_set():
            self._wake.wait(max(0.0, due - self._monotonic()))
            self._wake.clear()
            if self._stopping.is_set():
                break
            now = self._monotonic()
            if now < due:
                if self.pending() < FLUSH_SIZE:
                    continue
                gap = self._last_send + self._min_gap - now
                if gap > 0 and self._stopping.wait(gap):
                    break
            self.flush()
            due = self._monotonic() + self._interval
        if not self._discarded.is_set():
            self.flush()


class McpObserver:
    """Turns local MCP observations into usage events for whichever recorder is current.

    `recorder` returns the active UsageRecorder or None. Only registered tool names,
    outcomes, durations and the client's self-reported name and version are recorded,
    never arguments or results.
    """

    def __init__(self, recorder):
        self._recorder = recorder

    def client_connected(self, client_info):
        recorder = self._recorder()
        if recorder is None:
            return
        properties = client_properties(client_info)
        if properties is not None:
            recorder.record("mcp_client_connected", properties)

    def tool_called(self, tool, outcome, duration_ms):
        recorder = self._recorder()
        if recorder is None:
            return
        duration = min(max(int(duration_ms), 0), MAX_DURATION_MS)
        recorder.record(
            "mcp_tool_called", {"tool": tool, "outcome": outcome, "duration_ms": duration}
        )
