# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Owner-thread scheduling of receipt-bound result previews, without bpy.

The scheduler owns no thread and performs no network I/O or preview cache
work. Its owner calls ``pump`` from Blender's main-thread timer or a headless
loop. ``request`` reads saved receipts from the local job store, and ``release``
removes leftover private copies after the lane has stopped. Cache reads, private
copies, SDK metadata reads and downloads all run as tasks on the dedicated
preview lane of ``JobWorkers``; job refresh and downloads never wait for them.
Server previews can appear minutes after a result is saved, so missing ones,
and transfers that did not complete, are polled with backoff for a bounded
window of online time, then marked missing or failed until an explicit retry.
Stills of the assets a waiting workflow step lists for review use the same
lane, window and cache through ``request_review``; their entries are keyed
apart from saved results, so the same asset ID never shares state.
Cache maintenance runs with a batch at most every ``MAINTAIN_SECONDS``; after
previews were written, an idle scheduler queues a maintenance-only lane command
on the same cadence, so the cache budget does not wait for the next poll.
Audio envelope copies are decoded by a lane command that runs an owned offline
Blender process; image copies wait for Blender's main thread through
``decode_requests``. ``watch`` signals a wait on another thread, such as a local
MCP request, once results stop changing by themselves; their statuses are still
read on the owner thread.
"""

import math
import os
import threading
import time
from concurrent.futures import CancelledError
from dataclasses import dataclass, field
from pathlib import Path

from . import result_previews as previews
from .workers import WorkerError

State = previews.PreviewState
WINDOW_SECONDS = 300.0
POLL_DELAYS = (5.0, 10.0, 20.0, 40.0, 60.0)
OFFLINE_DELAY = 5.0
BATCH_LIMIT = 32
DECODE_LIMIT = 4
DECODE_SECONDS = 120.0
MAINTAIN_SECONDS = 600.0
NO_WAVEFORM = "Audio waveforms need Blender's executable"
CANCELED = "Preview decoding was canceled; use Retry"
ENTRY_LIMIT = 256
WATCH_LIMIT = 8
# Renditions that the next lane batch must resolve.
_ACTIVE = frozenset({State.QUEUED, State.PENDING, State.OFFLINE})
_SETTLED = frozenset({State.READY, State.MISSING, State.FAILED, State.UNSUPPORTED})
# States that change no further without Online Access or an explicit request.
QUIET = _SETTLED | {State.OFFLINE}


@dataclass(frozen=True)
class RenditionStatus:
    state: State
    preview: previews.CachedPreview | None = None
    request: previews.DecodeRequest | None = field(default=None, repr=False)
    reason: str | None = None


@dataclass(frozen=True)
class PreviewStatus:
    """An immutable snapshot for drawing or MCP; it holds no live task or lock."""

    request_id: str
    asset_id: str
    media_type: str
    kind: str | None
    renditions: tuple[tuple[str, RenditionStatus], ...]

    def get(self, rendition):
        return dict(self.renditions).get(rendition)


class PreviewWatch:
    """Tells any thread when watched results have no rendition still in progress.

    In progress means queued, pending or decoding. An offline rendition waits
    for Online Access, so it counts as quiet. ``renditions``, when set, limits
    the watch to those renditions of each result. The scheduler's owner thread
    sets the signal while it pumps, and on close; statuses must still be read
    there.
    """

    __slots__ = ("_event", "keys", "renditions")

    def __init__(self, keys, renditions=None):
        self.keys = keys
        self.renditions = renditions
        self._event = threading.Event()

    def wait(self, timeout=None):
        """Whether the watched results became quiet within ``timeout`` seconds."""
        return self._event.wait(timeout)

    @property
    def quiet(self):
        return self._event.is_set()


class _Entry:
    __slots__ = (
        "attempts",
        "canceled",
        "due",
        "force",
        "hold",
        "inflight",
        "poll",
        "renew",
        "retry",
        "seen",
        "states",
        "target",
        "used",
        "window",
    )

    def __init__(self, target, now):
        self.target = target
        self.states = {}
        # Earliest pump that has work for this entry: now for queued renditions,
        # ``poll`` for waiting ones, never once every rendition has settled.
        self.due = now
        # Backoff for pending or offline renditions; queued ones never wait for it.
        self.poll = now
        self.attempts = 0
        # Online polling window: its start, or None while paused or unopened,
        # with the online seconds already consumed before a pause.
        self.window = None
        self.used = 0.0
        self.force = False
        # An explicit retry received while this entry's batch was in flight:
        # its renditions already read queued; the restart follows that batch.
        self.retry = False
        # A cancel received after that retry: the restart queues only server
        # renditions, so the local ones it failed stay canceled.
        self.hold = False
        # A rendition added while this entry's batch was in flight, so that
        # batch's final flag predates the new window.
        self.renew = False
        self.inflight = False
        # Local decoding canceled while this entry's batch was in flight: the
        # decode request the batch returns is discarded instead of issued.
        self.canceled = False
        self.seen = now


class ResultPreviewScheduler:
    """Track preview requests for one connection and feed its preview lane.

    Use from the creating thread only, normally Blender's main thread. Status
    snapshots never trigger I/O, so drawing code can read them safely.
    """

    def __init__(
        self,
        workers,
        coordinator,
        root,
        *,
        clock=time.monotonic,
        window=WINDOW_SECONDS,
        delays=POLL_DELAYS,
        batch_limit=BATCH_LIMIT,
        decode_limit=DECODE_LIMIT,
        decode_seconds=DECODE_SECONDS,
        waveform=None,
    ):
        if (
            not callable(clock)
            or not delays
            or any(
                type(value) not in (int, float) or not math.isfinite(value) or value <= 0
                for value in (window, decode_seconds, *delays)
            )
        ):
            raise ValueError("Use positive finite preview polling intervals")
        for value in (batch_limit, decode_limit):
            if type(value) is not int or value < 1:
                raise ValueError("Use positive preview batch and decode limits")
        self._owner = threading.current_thread()
        self._workers, self._coordinator = workers, coordinator
        self._root = os.fspath(root)
        self._clock = clock
        self._window, self._delays = float(window), tuple(float(value) for value in delays)
        self._batch_limit, self._decode_limit = batch_limit, decode_limit
        self._decode_seconds = float(decode_seconds)
        # The owned offline decoder for audio envelopes; without one they fail.
        self._waveform = waveform
        self._entries = {}
        self._task = None
        self._batch = ()
        self._issued = {}
        self._publishing = {}
        # Publications whose local decode ``cancel`` signaled; their failure
        # leaves the canceled or restarted rendition state alone.
        self._canceled = set()
        self._discards = []
        self._watches = []
        self._maintained = None
        # A maintenance-only lane command, and whether previews were written to
        # the cache since the last pass, which may have taken it over budget.
        self._maintenance = None
        self._written = False
        self._closed = False

    def _check(self):
        if threading.current_thread() is not self._owner:
            raise RuntimeError("Use result previews from their owning thread")
        if self._closed:
            raise previews.PreviewError("Result previews for this connection are closed")

    @property
    def closed(self):
        return self._closed

    @property
    def root(self):
        """The private cache root passed to every lane command."""
        return Path(self._root)

    def _snapshot(self, entry):
        target = entry.target
        return PreviewStatus(
            target.request_id,
            target.asset_id,
            target.media_type,
            target.kind,
            tuple(entry.states.items()),
        )

    def _make_room(self):
        settled = sorted(
            (
                (entry.seen, key)
                for key, entry in self._entries.items()
                if not entry.inflight
                and all(status.state in _SETTLED for status in entry.states.values())
            ),
            key=lambda item: item[0],
        )
        for _, key in settled[: max(0, len(self._entries) - ENTRY_LIMIT + 1)]:
            del self._entries[key]
        if len(self._entries) >= ENTRY_LIMIT:
            raise previews.PreviewError("Too many result previews are pending; try again shortly")

    @staticmethod
    def _key(target):
        """Entries of a review asset never share state with a saved result's."""
        return target.request_id, target.asset_id, target.kind == previews.REVIEW

    def request(self, request_id, *, asset_ids=None, clip=False, renditions=None):
        """Track previews for a saved job's downloaded assets and return their status.

        Server stills are polled; clips are fetched only when ``clip`` is true.
        ``renditions`` limits the request to some of a kind's renditions, such
        as only a local audio envelope, which never contacts Scenario.
        Requesting again keeps existing state; use ``retry`` after a failure.
        Adding a rendition opens a new polling window for that result.
        """
        self._check()
        if renditions is not None:
            renditions = tuple(renditions)
            if not renditions or not set(renditions) <= set(previews.RENDITIONS):
                raise previews.PreviewError("Request supported preview renditions")
        targets = self._coordinator.result_preview_targets(request_id, asset_ids)
        return self._track(targets, clip=clip, renditions=renditions)

    def request_review(self, request_id, asset_ids):
        """Track stills of the assets a saved workflow job's waiting step lists.

        The caller owns the step projection and passes its review asset IDs.
        Stills come from Scenario through the same lane, polling window and
        cache as server previews, bound to the saved workflow job. Requesting
        again keeps existing state; use ``retry(..., review=True)`` after a
        failure.
        """
        self._check()
        targets = self._coordinator.review_preview_targets(request_id, tuple(asset_ids))
        return self._track(targets)

    def _track(self, targets, *, clip=False, renditions=None):
        now = self._clock()
        result = []
        for target in targets:
            key = self._key(target)
            entry = self._entries.get(key)
            if entry is None or entry.target != target:
                if entry is None and len(self._entries) >= ENTRY_LIMIT:
                    self._make_room()
                if entry is not None:
                    self._release(entry)
                entry = self._entries[key] = _Entry(target, now)
            entry.seen = now
            wanted = previews.renditions(target.kind, clip=clip)
            if renditions is not None:
                wanted = tuple(rendition for rendition in wanted if rendition in renditions)
            if not wanted:
                entry.states.setdefault(
                    previews.STILL,
                    RenditionStatus(
                        State.UNSUPPORTED, reason="No preview is available for this format"
                    ),
                )
            added = [rendition for rendition in wanted if rendition not in entry.states]
            for rendition in added:
                entry.states[rendition] = RenditionStatus(State.QUEUED)
            if added:
                # A newly requested rendition, such as a clip after the still,
                # gets a full window even if earlier polling used or ended one.
                # Renditions still polling share it, so their window restarts,
                # including those whose final poll is on the lane right now.
                entry.window, entry.used, entry.attempts = None, 0.0, 0
                entry.renew |= entry.inflight
                entry.due = min(entry.due, now)
            result.append(self._snapshot(entry))
        return tuple(result)

    def retry(self, request_id, asset_id, *, review=False):
        """Explicitly fetch again, clearing a missing marker and the polling window.

        Every rendition except unsupported ones and decoded previews being
        published is queued at once, and its outstanding decode request is
        withdrawn, so the returned snapshot and ``status`` report the retry.
        While a lane batch for this result is in flight, the fetch waits for
        it: the pump that collects that batch applies its outcome and queues
        the renditions again in the same call, so a late outcome is never
        reported as settled and cannot undo the retry. A ``cancel`` received
        before then keeps the local renditions it fails canceled.
        ``review`` selects a workflow review asset rather than a saved result.
        """
        self._check()
        entry = self._entries.get((request_id, asset_id, review is True))
        if entry is None:
            raise previews.PreviewError("Request a preview for this saved result first")
        if entry.inflight:
            self._requeue(entry)
            entry.retry, entry.hold = True, False
        else:
            self._restart(entry, self._clock())
        return self._snapshot(entry)

    def cancel(self, request_id, asset_id):
        """Stop local decoding for one result; its unfinished local renditions fail.

        Unfinished means queued, decoding or, after a failed lane batch, waiting
        for its next poll. Server stills and clips keep polling. An issued
        decode request is discarded and a running decode is signaled, which
        terminates its offline Blender process. A copy that an in-flight batch
        is still preparing is discarded when that batch returns. A retry still
        waiting for that batch then restarts server renditions only: local
        decoding starts again only on a later ``retry``.
        """
        self._check()
        # Saved results only: a workflow review asset has no local renditions.
        entry = self._entries.get((request_id, asset_id, False))
        if entry is None:
            return None
        key = entry.target.key
        for identity, (request, _) in tuple(self._issued.items()):
            if request.key == key:
                del self._issued[identity]
                self._discard(request)
        for task, request in self._publishing.items():
            if request.key == key:
                self._workers.cancel_preview(task)
                self._canceled.add(task)
        for rendition, status in tuple(entry.states.items()):
            # A failed lane batch leaves local renditions pending its next
            # poll, which would otherwise send them to the lane again.
            if previews.is_local(entry.target.kind, rendition) and (
                status.state in _ACTIVE or status.state == State.DECODE
            ):
                entry.states[rendition] = RenditionStatus(State.FAILED, reason=CANCELED)
        entry.canceled |= entry.inflight
        entry.hold |= entry.retry
        self._schedule(entry, self._clock())
        return self._snapshot(entry)

    def _requeue(self, entry, *, local=True):
        """Queue every rendition a retry fetches again and withdraw its decode requests.

        ``local=False`` leaves local renditions as they are, for a deferred
        retry that a later ``cancel`` overtook.
        """
        self._release(entry)
        publishing = {
            request.rendition
            for task, request in self._publishing.items()
            if request.key == entry.target.key and task not in self._canceled
        }
        for rendition, status in tuple(entry.states.items()):
            if status.state == State.UNSUPPORTED or rendition in publishing:
                continue
            if local or not previews.is_local(entry.target.kind, rendition):
                entry.states[rendition] = RenditionStatus(State.QUEUED)

    def _restart(self, entry, now):
        self._requeue(entry, local=not entry.hold)
        entry.force, entry.retry, entry.hold, entry.attempts = True, False, False, 0
        entry.canceled = False
        entry.window, entry.used = None, 0.0
        entry.poll = entry.due = now

    def status(self, request_id, asset_id, *, review=False):
        """Read the last known status; no I/O, safe while drawing."""
        if threading.current_thread() is not self._owner:
            raise RuntimeError("Use result previews from their owning thread")
        entry = self._entries.get((request_id, asset_id, review is True))
        return None if entry is None else self._snapshot(entry)

    def quiet(self, request_id, asset_id, renditions=None):
        """Whether no rendition of this result is queued, pending or decoding; no I/O.

        ``renditions`` limits the check to those renditions, such as the
        envelope a caller asked for while the result's still keeps polling.
        A retry deferred behind an in-flight batch already reads queued, so
        it is never reported quiet.
        """
        if threading.current_thread() is not self._owner:
            raise RuntimeError("Use result previews from their owning thread")
        return self._quiet((request_id, asset_id), self._renditions(renditions))

    @staticmethod
    def _renditions(renditions):
        if renditions is None:
            return None
        renditions = frozenset(renditions)
        if not renditions or not renditions <= set(previews.RENDITIONS):
            raise previews.PreviewError("Watch supported preview renditions")
        return renditions

    def _quiet(self, key, renditions=None):
        # A result never requested, or forgotten once settled, has nothing in progress.
        entry = self._entries.get(key)
        return entry is None or all(
            status.state in QUIET
            for rendition, status in entry.states.items()
            if renditions is None or rendition in renditions
        )

    def watch(self, request_id, asset_ids, renditions=None):
        """A signal for a wait off the owner thread, set once these results are quiet.

        ``renditions`` limits the wait to those renditions of each result, as
        for ``quiet``. The owner thread reads their statuses afterwards and
        calls ``unwatch``. Closing the scheduler sets every signal, so no wait
        outlives it.
        """
        self._check()
        renditions = self._renditions(renditions)
        if len(self._watches) >= WATCH_LIMIT:
            raise previews.PreviewError("Too many preview waits are open; try again shortly")
        watch = PreviewWatch(tuple((request_id, asset_id) for asset_id in asset_ids), renditions)
        self._watches.append(watch)
        self._notify()
        return watch

    def unwatch(self, watch):
        """Forget a watch; also safe after the scheduler closed."""
        if threading.current_thread() is not self._owner:
            raise RuntimeError("Use result previews from their owning thread")
        if watch in self._watches:
            self._watches.remove(watch)

    def _notify(self):
        for watch in tuple(self._watches):
            if all(self._quiet(key, watch.renditions) for key in watch.keys):
                self._watches.remove(watch)
                watch._event.set()

    def _release_watches(self):
        for watch in self._watches:
            watch._event.set()
        self._watches.clear()

    def decode_requests(self):
        """Outstanding image copies awaiting Blender-side decoding, oldest first.

        Audio envelope copies are never listed: the scheduler queues their
        decoding in an owned offline Blender process on the preview lane.
        """
        self._check()
        return tuple(
            request
            for request, _ in self._issued.values()
            if request.rendition != previews.ENVELOPE
        )

    def _issued_entry(self, request):
        item = self._issued.get(id(request))
        if item is None or item[0] is not request:
            raise previews.PreviewError("Use an outstanding decode request from these previews")
        return item

    def finish_decode(self, request, *, envelope=None):
        """Queue validation and caching of Blender's decoded still or envelope."""
        self._check()
        self._issued_entry(request)
        task = self._workers.finish_result_preview(request, root=self._root, envelope=envelope)
        del self._issued[id(request)]
        self._publishing[task] = request
        return task

    def discard_decode(self, request, *, reason="Blender could not decode this preview"):
        """Drop a decode request Blender could not complete; the rendition fails."""
        self._check()
        self._issued_entry(request)
        del self._issued[id(request)]
        self._set(request, RenditionStatus(State.FAILED, reason=reason))
        self._discard(request)

    def _discard(self, request):
        try:
            self._discards.append(
                (self._workers.discard_result_preview(request, root=self._root), request)
            )
        except WorkerError:
            # Retried by pump or release; the age sweep is the final backstop.
            self._discards.append((None, request))

    def _release(self, entry):
        for identity, (request, _) in tuple(self._issued.items()):
            if request.key == entry.target.key:
                del self._issued[identity]
                self._discard(request)

    def _entry_for(self, request):
        for entry in self._entries.values():
            if entry.target.key == request.key:
                return entry
        return None

    def _set(self, request, status):
        entry = self._entry_for(request)
        if entry is not None and request.rendition in entry.states:
            entry.states[request.rendition] = status

    def _delay(self, attempts):
        return self._delays[min(attempts, len(self._delays)) - 1]

    @staticmethod
    def _open_window(entry, now):
        if entry.window is None:
            # Resume a paused window: offline time never consumed it.
            entry.window = now - entry.used

    @staticmethod
    def _schedule(entry, now):
        """Queued renditions are due now, waiting ones at their poll, settled ones never."""
        due = math.inf
        for status in entry.states.values():
            if status.state == State.QUEUED:
                due = now
                break
            if status.state in _ACTIVE:
                due = min(due, entry.poll)
        entry.due = due

    def _consume_batch(self, now):
        task, batch = self._task, self._batch
        self._task, self._batch = None, ()
        for entry, _ in batch:
            entry.inflight = False
        self._apply_batch(task, batch, now)
        for entry, work in batch:
            target = entry.target
            renew, entry.renew = entry.renew, False
            entry.canceled = False
            if self._entries.get(self._key(target)) is entry:
                if entry.retry:
                    self._restart(entry, now)
                elif renew and work.final:
                    self._rejoin(entry, work.renditions)
            # Renditions held back by the decode limit, or requested while this
            # batch ran, stay queued and must not wait for another trigger.
            self._schedule(entry, now)

    @staticmethod
    def _rejoin(entry, sent):
        """Return what a final poll settled to the window a new rendition opened.

        That poll's final flag was frozen before the request, so renditions it
        left missing or failed poll again in the new window. Its outcomes do not
        say whether a failure came from the window's end, so a failed download
        also gets that poll. ``force`` clears the missing marker it wrote; the
        lane forgets markers for every rendition in the next batch, so a marker
        the added rendition kept from an earlier session is decided again too.
        Ready previews are kept.
        """
        for rendition in sent:
            status = entry.states.get(rendition)
            if status is not None and status.state in (State.MISSING, State.FAILED):
                entry.states[rendition] = RenditionStatus(State.QUEUED)
                entry.force = True

    def _apply_batch(self, task, batch, now):
        try:
            result = task.result()
        except (CancelledError, previews.PreviewCanceled):
            return
        except BaseException:
            # A stored lane outcome, never a signal for this thread: a control
            # exception already retired the workers. Retry other failures within
            # the same bounded window, then stop.
            for entry, work in batch:
                self._open_window(entry, now)
                expired = now - entry.window >= self._window
                for rendition in work.renditions:
                    if entry.states.get(rendition, RenditionStatus(State.QUEUED)).state in _ACTIVE:
                        entry.states[rendition] = RenditionStatus(
                            State.FAILED if expired else State.PENDING,
                            reason="Preview preparation failed; use Retry"
                            if expired
                            else "Preview preparation failed; retrying",
                        )
                entry.attempts += 1
                if not expired:
                    entry.poll = now + self._delay(entry.attempts)
            return
        if result.scope != self._coordinator.scope:
            for request in result.requests:
                self._discard(request)
            return
        for outcome in result.outcomes:
            target = outcome.target
            entry = self._entries.get(self._key(target))
            if entry is None or entry.target != target or self._closed:
                for item in outcome.renditions:
                    if item.request is not None:
                        self._discard(item.request)
                continue
            pending = offline = False
            for item in outcome.renditions:
                if item.request is not None and entry.canceled:
                    self._discard(item.request)
                    entry.states[item.rendition] = RenditionStatus(State.FAILED, reason=CANCELED)
                    continue
                entry.states[item.rendition] = RenditionStatus(
                    item.state, item.preview, item.request, item.reason
                )
                if item.request is not None:
                    self._issued[id(item.request)] = (item.request, now)
                pending |= item.state == State.PENDING
                offline |= item.state == State.OFFLINE
                # A cache hit counts too: the pass it triggers only evicts over budget.
                self._written |= item.state == State.READY
            if offline:
                # Pause the polling window: time without online access does not
                # consume it, and the next online poll resumes it.
                if entry.window is not None:
                    entry.used = now - entry.window
                    entry.window = None
                entry.poll = now + OFFLINE_DELAY
            elif pending:
                self._open_window(entry, now)
                entry.attempts += 1
                end = entry.window + self._window
                entry.poll = min(now + self._delay(entry.attempts), max(now, end))

    def _dispatch_envelopes(self):
        """Queue offline decoding of issued audio copies, oldest first.

        A full lane leaves the rest issued for the next pump; the decode
        expiry still bounds how long they wait.
        """
        changed = False
        for identity, (request, _) in tuple(self._issued.items()):
            if request.rendition != previews.ENVELOPE:
                continue
            if self._waveform is None:
                self.discard_decode(request, reason=NO_WAVEFORM)
                changed = True
                continue
            try:
                task = self._workers.decode_result_preview(
                    request, root=self._root, waveform=self._waveform
                )
            except WorkerError:
                break
            del self._issued[identity]
            self._publishing[task] = request
        return changed

    def _consume_publications(self):
        for task, request in tuple(self._publishing.items()):
            if not task.done():
                continue
            del self._publishing[task]
            canceled = task in self._canceled
            self._canceled.discard(task)
            try:
                preview = task.result()
            except CancelledError:
                self._discards.append((None, request))
                status = RenditionStatus(State.FAILED, reason="Preview publication was canceled")
            except BaseException as error:  # Stored lane outcome; see _consume_batch.
                reason = (
                    str(error)
                    if isinstance(error, previews.PreviewError)
                    else "The decoded preview could not be saved"
                )
                status = RenditionStatus(State.FAILED, reason=reason)
            else:
                # A decode that finished before its cancellation is still valid.
                status, canceled = RenditionStatus(State.READY, preview), False
                self._written = True
            if not canceled:
                self._set(request, status)

    def _consume_discards(self):
        remaining = []
        for task, request in self._discards:
            if task is None:
                try:
                    task = self._workers.discard_result_preview(request, root=self._root)
                except WorkerError:
                    remaining.append((None, request))
                    continue
            if not task.done():
                remaining.append((task, request))
        self._discards = remaining

    def _expire_decodes(self, now):
        for identity, (request, issued) in tuple(self._issued.items()):
            if now - issued >= self._decode_seconds:
                del self._issued[identity]
                self._set(
                    request,
                    RenditionStatus(State.FAILED, reason="Preview decoding did not finish; Retry"),
                )
                self._discard(request)

    def _next_batch(self, now):
        decodes = len(self._issued) + len(self._publishing)
        batch = []
        for entry in sorted(self._entries.values(), key=lambda item: item.due):
            if len(batch) >= self._batch_limit or entry.due > now:
                break
            sent = []
            for rendition, status in entry.states.items():
                if status.state not in _ACTIVE:
                    continue
                if status.state != State.QUEUED and entry.poll > now:
                    continue  # Waiting renditions keep their backoff.
                if previews.is_local(entry.target.kind, rendition):
                    if decodes >= self._decode_limit:
                        continue  # Still queued, so still due on the next pump.
                    decodes += 1
                sent.append(rendition)
            if not sent:
                self._schedule(entry, now)
                continue
            final = entry.window is not None and now - entry.window >= self._window
            batch.append(
                (entry, previews.PreviewWork(entry.target, tuple(sent), final, entry.force))
            )
        return batch

    def pump(self):
        """Collect lane results and queue the next due batch; returns whether state changed."""
        if threading.current_thread() is not self._owner:
            raise RuntimeError("Use result previews from their owning thread")
        if self._closed:
            return False
        try:
            return self._advance()
        finally:
            self._notify()

    def _advance(self):
        now = self._clock()
        changed = False
        if self._task is not None and self._task.done():
            self._consume_batch(now)
            changed = True
        if any(task.done() for task in self._publishing):
            self._consume_publications()
            changed = True
        if self._maintenance is not None and self._maintenance.done():
            # A stored lane outcome, as in _apply_batch: a failed pass is not
            # retried early; the next one is due after the usual interval.
            self._maintenance = None
        changed |= self._dispatch_envelopes()
        self._consume_discards()
        if self._issued:
            before = len(self._issued)
            self._expire_decodes(now)
            changed |= len(self._issued) != before
        if self._task is None:
            batch = self._next_batch(now)
            maintain = self._maintained is None or now - self._maintained >= MAINTAIN_SECONDS
            if batch:
                try:
                    self._task = self._workers.prepare_result_previews(
                        [work for _, work in batch], root=self._root, maintain=maintain
                    )
                except WorkerError:
                    return changed
                if maintain:
                    self._maintained, self._written = now, False
                self._batch = tuple(batch)
                for entry, _ in batch:
                    entry.inflight, entry.force = True, False
            elif maintain and self._written and self._maintenance is None:
                # No batch may come to maintain the cache once every rendition
                # has settled, so previews written since the last pass get a
                # maintenance-only command: no job read or network request.
                try:
                    self._maintenance = self._workers.maintain_result_previews(root=self._root)
                except WorkerError:
                    return changed
                self._maintained, self._written = now, False
        return changed

    def close(self):
        """Stop scheduling; cancel lane work. ``release`` frees copies after shutdown."""
        if threading.current_thread() is not self._owner:
            raise RuntimeError("Use result previews from their owning thread")
        self._closed = True
        self._release_watches()
        for task in (self._task, self._maintenance, *self._publishing):
            if task is not None:
                self._workers.cancel_preview(task)

    def release(self):
        """After the lane stops, remove every private copy this scheduler still owns."""
        if threading.current_thread() is not self._owner:
            raise RuntimeError("Use result previews from their owning thread")
        self._closed = True
        self._release_watches()
        requests = [request for request, _ in self._issued.values()]
        requests += list(self._publishing.values())
        requests += [request for _, request in self._discards]
        if self._task is not None and self._task.done():
            try:
                requests += list(self._task.result().requests)
            except BaseException:
                # A stored lane outcome, as in _apply_batch. A failed or canceled
                # batch discarded any private copies it made before it ended.
                pass
        for request in requests:
            previews.discard_directory(request.directory)
        self._issued.clear()
        self._publishing.clear()
        self._canceled.clear()
        self._discards.clear()
        self._task, self._batch, self._maintenance = None, (), None
        self._entries.clear()
