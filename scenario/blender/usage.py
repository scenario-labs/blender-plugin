# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in anonymous usage data: preference lifecycle, online-access mirror and event hooks.

**Share anonymous usage data** is off by default. Turning it on saves a random install ID
in the extension's user directory and records extension_started; turning it off discards
unsent events, stops the sender and deletes the ID. Only that update creates the ID, and
the ID file is the opt-in record every Blender process shares: a preference that reads on
without it (switched off in another Blender whose preferences were not saved) shares
nothing. core.telemetry.usage owns the queue and the sender thread, which rereads the two
Events below and the saved ID before each send. Only the main thread changes the Events:
the preference, and tick on every pump tick.

A window session records from registration. Background Blender records only inside the
scenario_blender command, whose loop keeps the online-access mirror current; other
background runs have no main-thread tick to follow a change of Allow Online Access.

Operator events come from wrappers around the extension's own operators, installed after
registration: Blender looks an operator's execute, invoke, modal and cancel up on its class
at each call, so a replaced method takes effect, while registration only checks which of
them exist and their argument counts. The wrappers keep those counts and are removed on
unregister. With sharing off a wrapper costs one global read.
"""

import functools
import logging
import math
import pathlib
import threading
import time
import types

import bpy

from .. import __version__
from ..core.telemetry import relay
from ..core.telemetry import usage as events
from ..mcp import server as mcp_server
from . import runtime

log = logging.getLogger("scenario.usage")

# Operators that are not a user's action, or that fire at high frequency. What they start
# is still counted: the composer's Generate, Settings and model chip run their own operators.
EXCLUDED_OPERATORS = frozenset(
    {
        # A MOUSEMOVE keymap item invokes it on every pointer move over a 3D view, and its
        # modal then sees every event while the floating composer is engaged.
        "scenario.composer_modal",
        # The pump runs it to show a feedback send's outcome in the status bar.
        "scenario.feedback_outcome",
        # The usage data card: an answer to it, No thanks above all, is never recorded.
        "scenario.usage_card",
    }
)
_METHODS = ("execute", "invoke", "modal", "cancel")
# The scenario_blender command waits this long for its last send before Blender exits.
FINAL_SEND_WAIT = relay.TIMEOUT + 1.0
# Unregistering in a window session, at quit too, waits at most this long for it.
TEARDOWN_SEND_WAIT = 1.0
# How often the tick compares the saved install ID with the running recorder's.
ID_CHECK_INTERVAL = 5.0
_ORIGINAL = "_scenario_usage_original"

# Worker-safe permissions for the sender thread and local MCP's HTTP threads.
_sharing = threading.Event()
_online = threading.Event()
_recorder = None  # the running events.UsageRecorder, or None while sharing is off
_active = False  # a window session, or the scenario_blender command
_send = None  # tests replace the HTTP POST
_start_recorded = False  # extension_started queued for this install ID in this process
_last_id_check = -math.inf  # time.monotonic() of the tick's last install ID comparison
_pending_delete = None  # an opted-out install ID whose file could not be deleted yet
_calls = threading.local()  # depth of wrapped operator calls on this thread
_instrumented = {}  # operator class -> {method: its own original, or None when inherited}

# Local MCP reports through this observer; it records only while sharing is running.
MCP_OBSERVER = events.McpObserver(lambda: _recorder)


def state_dir():
    return pathlib.Path(bpy.utils.extension_path_user(runtime.PACKAGE, path="state", create=True))


def blender_version():
    return "{}.{}.{}".format(*bpy.app.version[:3])


def sharing_enabled():
    prefs = runtime.prefs()
    return bool(prefs is not None and getattr(prefs, "share_usage", False))


def recorder():
    """The running recorder, or None; tests read its queue."""
    return _recorder


def install_id():
    """The install ID while sharing is on, else None; feedback carries it only then.

    As for events, the saved file is the opt-in record: a preference that reads on
    without it shares nothing, so the file is read rather than the recorder's copy.
    """
    if not sharing_enabled():
        return None
    try:
        return events.read_install_id(state_dir())
    except OSError:
        return None


# -- lifecycle -----------------------------------------------------------------
def register():
    instrument_operators()
    if not bpy.app.background:
        activate()


def unregister():
    shutdown()
    restore_operators()


def shutdown():
    """Stop at unregister; a window session waits up to TEARDOWN_SEND_WAIT for the last send.

    Blender may exit right after, ending the daemon sender thread, so the wait is short.
    """
    deactivate(wait=TEARDOWN_SEND_WAIT)


def activate(*, send=None):
    """Allow recording in this session; starts the sender when the preference is on."""
    global _active, _send
    _active, _send = True, send
    _sync()


def deactivate(*, wait=None):
    """Stop recording; a last send goes out only if the live settings still permit it.

    The worker-safe Events are as of the last tick: Revert to Saved Preferences, Load Factory
    Preferences or switching Allow Online Access off may have come since. So this main-thread
    call rereads the preference and online access first and discards everything when either
    is withdrawn. Otherwise it waits up to `wait` seconds, and only while events are queued
    or a send is in flight.
    """
    global _active
    _active = False
    if not (sharing_enabled() and runtime.online()):
        _stop(discard=True)
        return
    recorder = _recorder
    busy = recorder is not None and recorder.permitted() and recorder.busy()
    _stop(discard=False, wait=wait if busy else None)


def set_sharing(enabled):
    """The preference's update: on saves an ID and starts, off forgets everything."""
    global _start_recorded, _pending_delete
    if enabled:
        if _pending_delete is not None:
            _forget_install_id(_pending_delete)  # finish the last opt-out first, if it can
            _pending_delete = None
        try:
            directory = state_dir()
            if events.read_install_id(directory) is None:
                events.create_install_id(directory)
                _start_recorded = False  # a new opt-in is a new install
        except OSError as error:
            log.warning(
                "Usage data is not sent: its install ID was not saved (%s)", type(error).__name__
            )
            return
        _sync()
        return
    _sharing.clear()
    running = _recorder.install_id if _recorder is not None else None
    _stop(discard=True)
    _forget_install_id(running)


def _forget_install_id(install_id=None):
    """Delete the opted-out ID; if that fails, the tick retries it while sharing stays off.

    The file is what other Blender processes check before each send, so it must go. A
    retry deletes only that ID, never a replacement saved since.
    """
    global _pending_delete
    try:
        directory = state_dir()
        install_id = install_id or events.read_install_id(directory)
        events.delete_install_id(directory, install_id)
    except OSError as error:
        if install_id is not None and install_id != _pending_delete:
            log.warning("The usage install ID was not deleted yet (%s)", type(error).__name__)
        _pending_delete = install_id
    else:
        _pending_delete = None


def follow_online_access():
    """Mirror Allow Online Access for worker threads; the main thread calls it every tick."""
    if runtime.online():
        _online.set()
    else:
        _online.clear()
    _record_start()


def tick():
    """Every main-loop tick: mirror online access and follow the opt-in.

    Revert to Saved Preferences and Load Factory Preferences change the preference without
    its update callback, so the tick turns sharing off the way the preference would. Every
    ID_CHECK_INTERVAL it also follows the saved install ID, which another Blender may have
    deleted or replaced (check_install_id).
    """
    global _last_id_check
    follow_online_access()
    prefs = runtime.prefs()  # None while preferences are unavailable: no decision then
    if prefs is None:
        return
    if not prefs.share_usage:
        if _recorder is not None:
            set_sharing(False)
        elif _pending_delete is not None:
            _forget_install_id(_pending_delete)
        return
    now = time.monotonic()
    if _active and now >= _last_id_check + ID_CHECK_INTERVAL:
        _last_id_check = now
        check_install_id()


def check_install_id():
    """Follow the saved install ID while the preference is on; main thread.

    Another Blender turning sharing off deletes the ID: this one stops and discards its
    queue. Turning it on again there saves a new ID: this one restarts under it, which is
    a new install, so extension_started is recorded again.
    """
    global _start_recorded
    try:
        saved = events.read_install_id(state_dir())
    except OSError:
        saved = None
    running = _recorder.install_id if _recorder is not None else None
    if saved == running:
        return
    if _recorder is not None:
        _sharing.clear()
        _stop(discard=True)  # its ID is gone: nothing queued under it may leave
    if saved is not None:
        _start_recorded = False
        _sync()


def _sync():
    global _recorder
    if not _active or not sharing_enabled():
        return
    if _recorder is None:
        try:
            directory = state_dir()
            install_id = events.read_install_id(directory)
        except OSError:  # never let usage data stop the extension from registering
            install_id = None
        if install_id is None:
            return  # no opt-in record: only turning the preference on creates one
        _sharing.set()
        recorder = events.UsageRecorder(
            install_id,
            relay.context(__version__, blender_version()),
            enabled=_sharing.is_set,
            online_access=_online.is_set,
            saved_install_id=functools.partial(events.read_install_id, directory),
            send=_send,
        )
        recorder.start()
        _recorder = recorder
    follow_online_access()


def _stop(*, discard, wait=None):
    global _recorder
    recorder, _recorder = _recorder, None
    if recorder is not None:
        recorder.stop(discard=discard, wait=wait)


def _record_start():
    """extension_started once per install ID and process, as soon as it can be sent."""
    global _start_recorded
    recorder = _recorder
    if recorder is not None and not _start_recorded and _online.is_set():
        _start_recorded = recorder.record("extension_started")


# -- operators -----------------------------------------------------------------
def _extension_operators():
    """Registered operator classes defined by this extension's modules."""
    pending, seen = list(bpy.types.Operator.__subclasses__()), set()
    while pending:
        cls = pending.pop()
        if cls in seen:
            continue
        seen.add(cls)
        pending.extend(cls.__subclasses__())
        module = getattr(cls, "__module__", "") or ""
        if (module == runtime.PACKAGE or module.startswith(runtime.PACKAGE + ".")) and getattr(
            cls, "is_registered", False
        ):
            yield cls


def instrument_operators():
    for cls in tuple(_extension_operators()):
        instrument(cls)


def restore_operators():
    for cls in tuple(_instrumented):
        restore(cls)


def instrument(cls):
    """Count the user's actions of one `scenario.*` operator; True when it was wrapped."""
    idname = getattr(cls, "bl_idname", None)
    if (
        cls in _instrumented
        or not isinstance(idname, str)
        or not idname.startswith("scenario.")
        or idname in EXCLUDED_OPERATORS
    ):
        return False
    originals = {}
    for name in _METHODS:
        method = getattr(cls, name, None)
        if not isinstance(method, types.FunctionType) or hasattr(method, _ORIGINAL):
            continue
        originals[name] = cls.__dict__.get(name)
        setattr(cls, name, _wrap(idname, name, method))
    _instrumented[cls] = originals
    return True


def restore(cls):
    """Put an instrumented operator's own methods back, so a reload starts clean."""
    for name, original in _instrumented.pop(cls, {}).items():
        if original is not None:
            setattr(cls, name, original)
        elif name in cls.__dict__:
            delattr(cls, name)


def _wrap(idname, name, method):
    # Blender checks each callback's positional argument count at registration.
    if name in ("execute", "cancel"):
        cancelling = name == "cancel"

        def wrapper(self, context):
            return _counted(idname, method, self, (context,), cancelling=cancelling)

    else:  # invoke and modal

        def wrapper(self, context, event):
            return _counted(idname, method, self, (context, event))

    functools.update_wrapper(wrapper, method)
    setattr(wrapper, _ORIGINAL, method)
    return wrapper


def _counted(idname, method, operator, args, *, cancelling=False):
    """Run the operator's method unchanged and record the outermost call's outcome.

    An invoke that calls execute, or an operator that runs another one, is one action:
    only the call that is not inside another wrapped call records. An invoke that opens
    a dialog, a file browser or a modal handler records nothing; the execute or modal
    that ends it does, or Blender's call of cancel (`cancelling`, which returns None)
    when the user closes the dialog without OK. An execute that calls its own cancel to
    clean up records only its own outcome. Calls made by a local MCP tool are the
    agent's, not the user's.
    Known overcount: Blender runs a REGISTER and UNDO operator's execute again for each
    change in the Adjust Last Operation panel, and each of those runs counts.
    """
    recorder = _recorder
    if recorder is None:
        return method(operator, *args)
    depth = getattr(_calls, "depth", 0)
    outermost = depth == 0 and not mcp_server.executing_tool()
    _calls.depth = depth + 1
    try:
        result = method(operator, *args)
    except Exception as error:
        if outermost:
            _record_operator(recorder, idname, "error", type(error).__name__)
        raise
    finally:
        _calls.depth = depth
    if outermost:
        outcome = "cancelled" if cancelling else _outcome(result)
        if outcome is not None:
            _record_operator(recorder, idname, outcome)
    return result


def _outcome(result):
    try:
        flags = set(result)
    except TypeError:
        return None
    if "RUNNING_MODAL" in flags or "INTERFACE" in flags:
        return None  # a dialog, file browser or modal handler: its ending reports
    if "FINISHED" in flags:
        return "finished"
    if "CANCELLED" in flags:
        return "cancelled"
    return None


def _record_operator(recorder, idname, outcome, error_type=None):
    try:
        recorder.record("operator_used", events.operator_properties(idname, outcome, error_type))
    except Exception:  # recording must never change what the operator did
        log.debug("Recording an operator event failed", exc_info=True)
