# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified collection and tag organization shared by the native Library and MCP.

No bpy imports and no persistence: reviews are session-local and the service
state read back after a write stays authoritative. Writes are unpaid account
mutations sent through the shared SDK adapter. A guard admits every write, the
first uncertain outcome stops further writes, and uncertainty is resolved by
reading back, never by sending again. The one resend is bounded: after the
service refuses a whole add because some assets were already members, only the
assets read back as not yet members are sent again, within ``ADD_ATTEMPTS`` add
requests in all.

The exact-name create guard, the in-session record of uncertain creates and
the read-back verification adapt Scenario Blender Studio's organization helpers
(``src/scenario_studio/organization.py`` at e2b0277064f0c502d46524fba1d006d0ac83f846,
original author Emmanuel de Maistre) from its remote-MCP catalog to SDKAdapter.
"""

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from ..api.sdk_adapter import (
    MAX_COLLECTION_ASSETS,
    MAX_TAG_CHANGES,
    AdapterError,
    AlreadyMembers,
    WriteRejected,
    WriteUncertain,
    _identifier,
    _organization_label,
)
from .store import JobScope, _identity

NOTICE = (
    "Organization changes are immediate Scenario account metadata. They use no "
    "credits, and Blender Undo does not reverse them."
)
REVIEW_TTL = 600.0
REVIEW_LIMIT = 32
LOOKUP_PAGE_SIZE = 100
LOOKUP_PAGES = 20
# Add requests one review may send when the service refuses an add because
# assets were already members, as another client can keep adding them.
ADD_ATTEMPTS = 3
_RAW_TAG_LIMIT = 200
_UNCERTAIN_CREATE = (
    "A previous create with this name has an unknown outcome; refresh collections "
    "before creating it again"
)
_EXISTING_NAME = "A collection with this exact name already exists; add the assets to it instead"


class Operation(StrEnum):
    ADD_TO_COLLECTION = "add_to_collection"
    REMOVE_FROM_COLLECTION = "remove_from_collection"
    UPDATE_TAGS = "update_tags"
    CREATE_COLLECTION = "create_collection"


class Outcome(StrEnum):
    """Per-asset (and created-collection) state after the verification read."""

    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNCONFIRMED = "UNCONFIRMED"
    NOT_SENT = "NOT_SENT"
    UNVERIFIED = "UNVERIFIED"


class ResultState(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNCONFIRMED = "UNCONFIRMED"
    REJECTED = "REJECTED"


class Phase(StrEnum):
    PREPARING = "PREPARING"
    READY = "READY"
    UNCHANGED = "UNCHANGED"
    REJECTED = "REJECTED"
    APPLYING = "APPLYING"
    FINISHED = "FINISHED"
    NOT_SENT = "NOT_SENT"
    DISCARDED = "DISCARDED"
    EXPIRED = "EXPIRED"


_TERMINAL = frozenset(
    {
        Phase.UNCHANGED,
        Phase.REJECTED,
        Phase.FINISHED,
        Phase.NOT_SENT,
        Phase.DISCARDED,
        Phase.EXPIRED,
    }
)


class OrganizationError(RuntimeError):
    """Safe text for UI and MCP boundaries; never service bodies, URLs or credentials."""


class OrganizationNotSent(OrganizationError):
    """No organization write was sent for this review."""


class DuplicateCollection(OrganizationNotSent):
    """The exact name already exists, so no create was sent."""

    def __init__(self, message=_EXISTING_NAME, collection_ids=()):
        super().__init__(message)
        self.collection_ids = tuple(collection_ids)


class OrganizationBusy(OrganizationError):
    """Review admission is full or another change is being applied."""


class ReviewUnavailable(OrganizationError):
    """The review is unknown here, expired, consumed or in another phase."""


def _opaque(value, label):
    try:
        return _identity(_identifier(value))
    except ValueError:
        raise ValueError(f"Use an opaque Scenario {label} ID") from None


def normalize_name(value):
    """Strip surrounding spaces, then apply the adapter's exact label rules."""
    if not isinstance(value, str):
        raise ValueError("Collection name must be text")
    return _organization_label(value.strip(), "Collection name")


def normalize_tags(values):
    """Return unique stripped tags in order; commas are reserved by the native field."""
    if values is None:
        return ()
    if isinstance(values, str) or not isinstance(values, (list, tuple)):
        raise ValueError("Tags must be a list of text labels")
    if len(values) > _RAW_TAG_LIMIT:
        raise ValueError(f"Use at most {_RAW_TAG_LIMIT} tag entries, counting duplicates")
    tags = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Tags must be text")
        value = value.strip()
        if "," in value:
            raise ValueError("Tags cannot contain commas")
        label = _organization_label(value, "Tag")
        if label not in tags:
            tags.append(label)
    if len(tags) > MAX_TAG_CHANGES:
        raise ValueError(f"Use at most {MAX_TAG_CHANGES} tags in one change")
    return tuple(tags)


def parse_tags(text):
    """Split the native comma-separated tags field, ignoring blank entries."""
    if not isinstance(text, str):
        raise ValueError("Tags must be text")
    return normalize_tags([part for part in text.split(",") if part.strip()])


@dataclass(frozen=True)
class OrganizationRequest:
    """One validated change request bound to the selected connection scope."""

    scope: JobScope
    operation: Operation
    asset_ids: tuple[str, ...] = ()
    collection_id: str | None = None
    collection_name: str | None = None
    add_tags: tuple[str, ...] = ()
    remove_tags: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.scope, JobScope):
            raise ValueError("Use the selected connection scope")
        if not isinstance(self.operation, Operation):
            raise ValueError("Choose a supported organization operation")
        operation = self.operation
        assets = self.asset_ids
        if not isinstance(assets, tuple) or len(assets) > MAX_COLLECTION_ASSETS:
            raise ValueError(f"Use at most {MAX_COLLECTION_ASSETS} asset IDs")
        for value in assets:
            _opaque(value, "asset")
        if len(set(assets)) != len(assets):
            raise ValueError("Asset IDs must be unique")
        if not assets and operation != Operation.CREATE_COLLECTION:
            raise ValueError("Choose at least one asset")
        for tags in (self.add_tags, self.remove_tags):
            if not isinstance(tags, tuple) or normalize_tags(list(tags)) != tags:
                raise ValueError("Use normalized, unique tags without commas")
        membership = operation in {Operation.ADD_TO_COLLECTION, Operation.REMOVE_FROM_COLLECTION}
        if membership:
            _opaque(self.collection_id, "collection")
        elif self.collection_id is not None:
            raise ValueError("A collection ID applies only to adding or removing assets")
        if operation == Operation.CREATE_COLLECTION:
            if normalize_name(self.collection_name) != self.collection_name:
                raise ValueError("Use a normalized collection name")
        elif self.collection_name is not None:
            raise ValueError("A collection name applies only to creating a collection")
        if operation == Operation.UPDATE_TAGS:
            if not self.add_tags and not self.remove_tags:
                raise ValueError("Add or remove at least one tag")
            if set(self.add_tags) & set(self.remove_tags):
                raise ValueError("A tag cannot be added and removed in the same change")
        elif self.add_tags or self.remove_tags:
            raise ValueError("Tags apply only to tag changes")


def build_request(
    scope,
    operation,
    *,
    asset_ids=(),
    collection_id=None,
    collection_name=None,
    add_tags=(),
    remove_tags=(),
):
    """Normalize UI or MCP arguments into one immutable request."""
    try:
        operation = Operation(operation)
    except ValueError:
        choices = ", ".join(item.value for item in Operation)
        raise ValueError(f"Choose one operation: {choices}") from None
    if isinstance(asset_ids, str) or not isinstance(asset_ids, (list, tuple)):
        raise ValueError("Use a list of asset IDs")
    if len(asset_ids) > MAX_COLLECTION_ASSETS:
        raise ValueError(f"Use at most {MAX_COLLECTION_ASSETS} asset IDs")
    return OrganizationRequest(
        scope,
        operation,
        tuple(asset_ids),
        collection_id,
        None if collection_name is None else normalize_name(collection_name),
        normalize_tags(add_tags),
        normalize_tags(remove_tags),
    )


@dataclass(frozen=True)
class AssetState:
    asset_id: str
    name: str
    tags: tuple[str, ...]
    collection_ids: tuple[str, ...]


@dataclass(frozen=True)
class AssetChange:
    """What one asset needs, computed from the fresh prepare read."""

    asset_id: str
    membership: bool = False
    add_tags: tuple[str, ...] = ()
    remove_tags: tuple[str, ...] = ()

    @property
    def changed(self):
        return self.membership or bool(self.add_tags or self.remove_tags)


@dataclass(frozen=True, eq=False)
class OrganizationSnapshot:
    """The fresh read a review shows; ``problem`` makes it unappliable."""

    plan_id: str
    request: OrganizationRequest
    assets: tuple[AssetState, ...] = ()
    missing: tuple[str, ...] = ()
    collection_name: str | None = None
    existing_collection_ids: tuple[str, ...] = ()
    changes: tuple[AssetChange, ...] = ()
    problem: str = ""

    @property
    def scope(self):
        return self.request.scope

    @property
    def request_count(self):
        """Writes apply sends when each one succeeds.

        An add refused because another client made some assets members after
        this read sends the rest again, up to ADD_ATTEMPTS add requests.
        """
        if self.problem:
            return 0
        changed = [change for change in self.changes if change.changed]
        operation = self.request.operation
        if operation == Operation.UPDATE_TAGS:
            return len(changed)
        if operation == Operation.CREATE_COLLECTION:
            return 1 + bool(self.request.asset_ids)
        return 1 if changed else 0


@dataclass(frozen=True)
class AssetOutcome:
    asset_id: str
    state: Outcome
    status: int | None = None
    tags: tuple[str, ...] | None = None
    collection_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, eq=False)
class OrganizationResult:
    plan_id: str
    scope: JobScope
    operation: Operation
    state: ResultState
    outcomes: tuple[AssetOutcome, ...]
    collection_id: str | None
    created_collection_id: str | None
    create_outcome: Outcome | None
    create_status: int | None
    requests_sent: int
    message: str


def _texts(record, key):
    values = record.get(key)
    return tuple(values) if isinstance(values, list) else ()


def _asset_state(record):
    name = record.get("name")
    return AssetState(
        record["id"],
        name if isinstance(name, str) else "",
        _texts(record, "tags"),
        _texts(record, "collectionIds"),
    )


def _change(request, state):
    operation = request.operation
    if operation == Operation.UPDATE_TAGS:
        return AssetChange(
            state.asset_id,
            add_tags=tuple(tag for tag in request.add_tags if tag not in state.tags),
            remove_tags=tuple(tag for tag in request.remove_tags if tag in state.tags),
        )
    if operation == Operation.CREATE_COLLECTION:
        return AssetChange(state.asset_id, membership=True)
    member = request.collection_id in state.collection_ids
    adding = operation == Operation.ADD_TO_COLLECTION
    return AssetChange(state.asset_id, membership=member != adding)


class OrganizationCommands:
    """Snapshot reads and guarded writes for one selected adapter.

    The owner admits at most one execution at a time. The record of names whose
    create outcome is unknown stays in this session only; the exact-name lookup
    still guards duplicate creates after a restart.
    """

    def __init__(self, adapter):
        self._adapter = adapter
        self._lock = threading.Lock()
        self._uncertain_names = set()

    def reset(self):
        with self._lock:
            self._uncertain_names.clear()

    def _uncertain(self, name):
        with self._lock:
            return name in self._uncertain_names

    def _mark_uncertain(self, name, uncertain=True):
        with self._lock:
            if uncertain:
                self._uncertain_names.add(name)
            else:
                self._uncertain_names.discard(name)

    def find_collections(self, name):
        """Return IDs of collections with exactly this name, reading bounded pages."""
        matches, seen, token = [], set(), None
        for _ in range(LOOKUP_PAGES):
            page = self._adapter.collection_page(page_size=LOOKUP_PAGE_SIZE, pagination_token=token)
            matches.extend(
                record["id"] for record in page["collections"] if record.get("name") == name
            )
            token = page["next_pagination_token"]
            if token is None:
                return tuple(dict.fromkeys(matches))
            if token in seen:
                raise OrganizationError("Scenario repeated a collection page; refresh collections")
            seen.add(token)
        raise OrganizationError(
            "Too many collections to check this name; add the assets to an existing collection"
        )

    def snapshot(self, request):
        """Read the current state a review shows. This sends no write."""
        if not isinstance(request, OrganizationRequest):
            raise OrganizationError("Prepare a validated organization request")
        records = self._adapter.asset_records(list(request.asset_ids)) if request.asset_ids else {}
        assets = tuple(_asset_state(records[a]) for a in request.asset_ids if a in records)
        missing = tuple(a for a in request.asset_ids if a not in records)
        operation = request.operation
        collection_name, existing, problem = None, (), ""
        if missing:
            problem = (
                f"{len(missing)} of {len(request.asset_ids)} assets were not found "
                "in the selected connection"
            )
        if operation in {Operation.ADD_TO_COLLECTION, Operation.REMOVE_FROM_COLLECTION}:
            record = self._adapter.collection(request.collection_id)
            name = record.get("name")
            collection_name = name if isinstance(name, str) else ""
        elif operation == Operation.CREATE_COLLECTION:
            existing = self.find_collections(request.collection_name)
            if existing:
                problem = problem or _EXISTING_NAME
            elif self._uncertain(request.collection_name):
                problem = problem or _UNCERTAIN_CREATE
        return OrganizationSnapshot(
            uuid.uuid4().hex,
            request,
            assets,
            missing,
            collection_name,
            existing,
            tuple(_change(request, state) for state in assets),
            problem,
        )

    def execute(self, snapshot, guard: Callable[[], None]):
        """Send an approved snapshot's writes and verify them by reading back.

        Nothing is resent after an uncertain outcome. After an add refused as
        AlreadyMembers, which writes nothing, the assets read back as not yet
        members are sent again, within ADD_ATTEMPTS add requests in all.
        ``guard`` runs before every write and raises when the context is no
        longer active; it never runs after the last write. Raises
        OrganizationNotSent only when no write was sent.
        """
        if (
            not isinstance(snapshot, OrganizationSnapshot)
            or snapshot.problem
            or not snapshot.request_count
        ):
            raise OrganizationNotSent("Prepare a ready organization review first")
        if not callable(guard):
            raise TypeError("An active-context guard is required")
        return _Execution(self, snapshot, guard).run()


@dataclass(frozen=True)
class _Write:
    kind: str  # "ok", "rejected", "uncertain" or "unsent"
    status: int | None = None


class _Execution:
    def __init__(self, commands, snapshot, guard):
        self.commands = commands
        self.adapter = commands._adapter
        self.snapshot = snapshot
        self.request = snapshot.request
        self.guard = guard
        self.writes = {}
        self.requests = 0
        self.stopped = False
        self.note = ""
        self.info = ""  # already-member count after a refused add; never a stop reason
        self.collection_id = self.request.collection_id
        self.created_id = None
        self.create = None  # _Write for the collection create, or None

    def admit(self):
        """Run the guard immediately before a write; a failure stops later writes."""
        try:
            self.guard()
        except Exception:
            unsent = "later changes were not sent" if self.requests else "nothing was sent"
            self.stop(f"The Scenario connection changed; {unsent}")
            return False
        return True

    def stop(self, note):
        self.stopped = True
        self.note = self.note or note

    def send(self, call):
        try:
            value = call()
        except WriteRejected as error:
            self.requests += 1
            # Adapter rejection text is sanitized and keyed by status class. An
            # already-member refusal is resolved by change_membership instead.
            if not isinstance(error, AlreadyMembers):
                self.note = self.note or str(error)
            return _Write("rejected", error.status), error
        except WriteUncertain as error:
            self.requests += 1
            return _Write("uncertain", error.status), error
        except (AdapterError, ValueError) as error:
            # The adapter raises plain errors (closed client, online access off)
            # and validation errors before dispatch.
            return _Write("unsent"), error
        except Exception:
            # Unexpected failures cannot be proven unsent; never treat as safe.
            self.requests += 1
            return _Write("uncertain"), None
        self.requests += 1
        return _Write("ok"), value

    def run(self):
        operation = self.request.operation
        if operation == Operation.CREATE_COLLECTION:
            self.create_collection()
        if operation == Operation.UPDATE_TAGS:
            self.update_tags()
        elif self.collection_id is not None and (
            operation != Operation.CREATE_COLLECTION or self.request.asset_ids
        ):
            self.change_membership()
        if not self.requests:
            raise OrganizationNotSent(self.note or "No organization change was sent")
        return self.verify()

    def create_collection(self):
        name = self.request.collection_name
        try:
            existing = self.commands.find_collections(name)
        except (OrganizationError, AdapterError) as error:
            raise OrganizationNotSent(str(error)) from None
        except Exception:
            # The lookup only reads, so nothing was sent; never echo unknown text.
            raise OrganizationNotSent("Could not check existing collection names") from None
        if existing:
            raise DuplicateCollection(collection_ids=existing)
        if self.commands._uncertain(name):
            raise OrganizationNotSent(_UNCERTAIN_CREATE)
        if not self.admit():
            raise OrganizationNotSent(self.note)
        write, value = self.send(lambda: self.adapter.create_collection(name))
        if write.kind == "unsent":
            raise OrganizationNotSent(str(value))
        self.create = write
        if write.kind == "ok":
            self.collection_id = self.created_id = value["id"]
        elif write.kind == "rejected":
            self.stop("Scenario refused to create the collection")
        else:
            self.commands._mark_uncertain(name)
            self.reconcile_create(name, getattr(value, "collection_id", None))

    def reconcile_create(self, name, acknowledged):
        """Resolve an uncertain create with one read, never with another create."""
        confirmed = None
        try:
            if acknowledged is not None:
                self.created_id = acknowledged
                record = self.adapter.collection(acknowledged)
                if record.get("name") == name:
                    confirmed = acknowledged
            else:
                found = self.commands.find_collections(name)
                if len(found) == 1:
                    confirmed = self.created_id = found[0]
        except Exception:
            confirmed = None
        if confirmed is None:
            self.stop(
                "Scenario did not confirm the new collection; refresh collections to "
                "inspect it before adding assets"
            )
            return
        self.commands._mark_uncertain(name, False)
        self.collection_id = confirmed
        self.create = _Write("reconciled")

    def change_membership(self):
        """Send one membership change; after an AlreadyMembers add, send the rest.

        The service refuses an add as a whole, writing nothing, when any asset
        is already a member. One read then drops the assets now in the
        collection, and the guard admits one more add for the others. A failed
        read, a refusal the read cannot explain, any other outcome or the
        ADD_ATTEMPTS bound ends the loop.
        """
        targets = [change.asset_id for change in self.snapshot.changes if change.membership]
        removing = self.request.operation == Operation.REMOVE_FROM_COLLECTION
        if removing:
            method = self.adapter.remove_collection_assets
        else:
            method = self.adapter.add_collection_assets
        total, present, attempts = len(targets), 0, 0
        while targets and not self.stopped and self.admit():
            attempts += 1
            write, value = self.send(lambda batch=list(targets): method(self.collection_id, batch))
            for asset_id in targets:
                self.writes[asset_id] = write
            if write.kind == "unsent":
                self.stop(str(value))
            elif write.kind == "uncertain":
                self.stop("Scenario did not confirm the collection change")
            if removing or not isinstance(value, AlreadyMembers):
                break
            if attempts == ADD_ATTEMPTS:
                self.stop(
                    f"Scenario still refused the add after {ADD_ATTEMPTS} requests because "
                    "more assets were already in the collection; prepare the rest again"
                )
                return
            members, targets = self.read_members(targets)
            if not members:
                self.stop(str(value))
                break
            present += len(members)
        if present == total == 1:
            self.info = "The asset was already in the collection"
        elif present == total:
            self.info = f"All {total} assets were already in the collection"
        elif present:
            again = "; the rest were sent again" if attempts > 1 else ""
            self.info = f"Already in the collection: {present} of {total} assets{again}"

    def read_members(self, targets):
        """Split targets into those read back as members and those to send again.

        Assets the read omits are neither: they are not sent again. A failed
        read proves nothing, so it returns no members.
        """
        try:
            records = self.adapter.asset_records(list(targets))
        except Exception:
            return set(), []
        members = {
            asset_id
            for asset_id in targets
            if asset_id in records
            and self.collection_id in _texts(records[asset_id], "collectionIds")
        }
        rest = [asset_id for asset_id in targets if asset_id in records and asset_id not in members]
        return members, rest

    def update_tags(self):
        for change in self.snapshot.changes:
            if not (change.add_tags or change.remove_tags):
                continue
            if self.stopped or not self.admit():
                return
            write, value = self.send(
                lambda change=change: self.adapter.update_asset_tags(
                    change.asset_id, add=list(change.add_tags), remove=list(change.remove_tags)
                )
            )
            self.writes[change.asset_id] = write
            if write.kind == "unsent":
                self.stop(str(value))
            elif write.kind == "uncertain":
                self.stop("Scenario did not confirm a tag change; later assets were not sent")

    def desired(self, record):
        operation = self.request.operation
        if operation == Operation.UPDATE_TAGS:
            tags = set(_texts(record, "tags"))
            return set(self.request.add_tags) <= tags and not set(self.request.remove_tags) & tags
        member = self.collection_id in _texts(record, "collectionIds")
        return member != (operation == Operation.REMOVE_FROM_COLLECTION)

    def classify(self, change, records):
        """Name the state an asset was read back in, never assuming an unread change."""
        asset_id = change.asset_id
        record = records.get(asset_id) if records is not None else None
        tags = _texts(record, "tags") if record is not None else None
        memberships = _texts(record, "collectionIds") if record is not None else None
        write = self.writes.get(asset_id)

        def outcome(state, status=None):
            return AssetOutcome(asset_id, state, status, tags, memberships)

        if record is not None and self.desired(record):
            return outcome(Outcome.VERIFIED)
        if not change.changed:
            # Nothing was sent for this asset: it was already in place when reviewed.
            return outcome(Outcome.NOT_SENT if record is not None else Outcome.UNVERIFIED)
        if write is None or write.kind == "unsent":
            return outcome(Outcome.NOT_SENT)
        if write.kind == "rejected":
            # A refused multi-asset request is not proof no member changed;
            # only the read shows the state (AlreadyMembers wrote nothing).
            single = self.request.operation == Operation.UPDATE_TAGS
            definite = record is not None or single
            return outcome(Outcome.REJECTED if definite else Outcome.UNVERIFIED, write.status)
        if write.kind == "uncertain" or record is not None:
            # Acknowledged but not observed (for example a dropped DELETE body),
            # or not acknowledged at all: never report it as applied or unsent.
            return outcome(Outcome.UNCONFIRMED, write.status)
        return outcome(Outcome.UNVERIFIED)

    def verify_create(self):
        if self.create is None:
            return None, None
        if self.create.kind == "rejected":
            return Outcome.REJECTED, self.create.status
        if self.create.kind == "reconciled":
            return Outcome.VERIFIED, None
        if self.create.kind != "ok":
            return Outcome.UNCONFIRMED, self.create.status
        try:
            record = self.adapter.collection(self.created_id)
        except Exception:
            return Outcome.UNVERIFIED, None
        if record.get("name") == self.request.collection_name:
            return Outcome.VERIFIED, None
        return Outcome.UNCONFIRMED, None

    def verify(self):
        records = None
        if any(write.kind != "unsent" for write in self.writes.values()):
            try:
                records = self.adapter.asset_records(list(self.request.asset_ids))
            except Exception:
                records = None
        outcomes = tuple(self.classify(change, records) for change in self.snapshot.changes)
        create_outcome, create_status = self.verify_create()
        states = [outcome.state for outcome in outcomes]
        if create_outcome is not None:
            states.append(create_outcome)
        if all(state == Outcome.VERIFIED for state in states):
            state, text = ResultState.VERIFIED, "Scenario confirmed every change"
        elif any(state in {Outcome.UNCONFIRMED, Outcome.UNVERIFIED} for state in states):
            state, text = (
                ResultState.UNCONFIRMED,
                "Unconfirmed: refresh to inspect; nothing is resent automatically",
            )
        elif Outcome.VERIFIED in states:
            state, text = ResultState.PARTIAL, "Some changes were confirmed; review each asset"
        else:
            state, text = ResultState.REJECTED, "Scenario confirmed no change"
        return OrganizationResult(
            self.snapshot.plan_id,
            self.request.scope,
            self.request.operation,
            state,
            outcomes,
            self.collection_id,
            self.created_id,
            create_outcome,
            create_status,
            self.requests,
            ". ".join(part for part in (text, self.note, self.info) if part),
        )


@dataclass(eq=False)
class _Review:
    review_id: str
    request: OrganizationRequest
    phase: Phase = Phase.PREPARING
    snapshot: OrganizationSnapshot | None = None
    ready_at: float | None = None
    result: OrganizationResult | None = None
    message: str = ""
    existing_collection_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewStatus:
    review_id: str
    phase: Phase
    request: OrganizationRequest
    snapshot: OrganizationSnapshot | None
    result: OrganizationResult | None
    message: str
    expires_in: float | None
    existing_collection_ids: tuple[str, ...] = ()


class OrganizationReviews:
    """Pure review state shared by the native Library and local MCP.

    PREPARING becomes READY, UNCHANGED or REJECTED; a READY review applies
    once (APPLYING, then FINISHED or NOT_SENT) unless it expires or is
    discarded. Entries are bounded; only finished or discarded ones are
    evicted, and at most one review applies at a time.
    """

    def __init__(self, *, ttl=REVIEW_TTL, limit=REVIEW_LIMIT, clock=time.monotonic):
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not ttl > 0:
            raise ValueError("Use a positive review lifetime")
        if type(limit) is not int or limit < 1 or not callable(clock):
            raise ValueError("Use a positive review limit and a monotonic clock")
        self._ttl, self._limit, self._clock = float(ttl), limit, clock
        self._lock = threading.RLock()
        self._reviews = {}

    def _get(self, review_id):
        review = self._reviews.get(review_id) if isinstance(review_id, str) else None
        if review is None:
            raise ReviewUnavailable(
                "This organization review is unavailable in the current connection; "
                "refresh the Library to inspect assets"
            )
        if review.phase == Phase.READY and self._clock() - review.ready_at >= self._ttl:
            review.phase = Phase.EXPIRED
            review.message = "This review expired; prepare it again"
        return review

    @property
    def applying(self):
        with self._lock:
            return any(review.phase == Phase.APPLYING for review in self._reviews.values())

    def open(self, request):
        if not isinstance(request, OrganizationRequest):
            raise ValueError("Use a validated organization request")
        with self._lock:
            for review_id in tuple(self._reviews):
                self._get(review_id)
            if len(self._reviews) >= self._limit:
                evicted = next(
                    (key for key, item in self._reviews.items() if item.phase in _TERMINAL),
                    None,
                )
                if evicted is None:
                    raise OrganizationBusy(
                        "Apply or discard an organization review before preparing another"
                    )
                del self._reviews[evicted]
            review = _Review(uuid.uuid4().hex, request)
            self._reviews[review.review_id] = review
            return review.review_id

    def remove(self, review_id):
        """Forget a review whose preparation was never queued."""
        with self._lock:
            review = self._reviews.get(review_id)
            if review is not None and review.phase == Phase.PREPARING:
                del self._reviews[review_id]

    def prepared(self, review_id, snapshot):
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None or review.phase != Phase.PREPARING:
                return False
            if not isinstance(snapshot, OrganizationSnapshot) or snapshot.request != review.request:
                review.phase, review.message = Phase.REJECTED, "The prepared review did not match"
                return False
            review.snapshot = snapshot
            if snapshot.problem:
                review.phase, review.message = Phase.REJECTED, snapshot.problem
                review.existing_collection_ids = snapshot.existing_collection_ids
            elif not snapshot.request_count:
                review.phase = Phase.UNCHANGED
                review.message = "Nothing to change; the assets are already organized this way"
            else:
                review.phase, review.ready_at = Phase.READY, self._clock()
            return True

    def failed(self, review_id, message):
        with self._lock:
            review = self._reviews.get(review_id)
            if review is not None and review.phase == Phase.PREPARING:
                review.phase, review.message = Phase.REJECTED, message

    def begin_apply(self, review_id):
        """Consume a READY review once and return the snapshot to execute."""
        with self._lock:
            review = self._get(review_id)
            if review.phase == Phase.EXPIRED:
                raise ReviewUnavailable(review.message)
            if review.phase != Phase.READY:
                raise ReviewUnavailable("Apply only a ready organization review, once")
            if self.applying:
                raise OrganizationBusy("Wait for the current organization change to finish")
            review.phase = Phase.APPLYING
            return review.snapshot

    def abort_apply(self, review_id):
        """Return to READY when the apply command was never queued."""
        with self._lock:
            review = self._reviews.get(review_id)
            if review is not None and review.phase == Phase.APPLYING:
                review.phase = Phase.READY

    def not_sent(self, review_id, message, collection_ids=()):
        with self._lock:
            review = self._reviews.get(review_id)
            if review is not None and review.phase == Phase.APPLYING:
                review.phase, review.message = Phase.NOT_SENT, message
                review.existing_collection_ids = tuple(collection_ids)

    def finished(self, review_id, result):
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None or review.phase != Phase.APPLYING:
                return
            if (
                isinstance(result, OrganizationResult)
                and review.snapshot is not None
                and result.plan_id == review.snapshot.plan_id
            ):
                review.phase, review.result, review.message = Phase.FINISHED, result, result.message
            else:
                self._unknown(review, "Scenario returned an unexpected organization outcome")

    def unknown(self, review_id, message):
        """The apply outcome is unknown: report it as unconfirmed, never as unsent."""
        with self._lock:
            review = self._reviews.get(review_id)
            if review is not None and review.phase == Phase.APPLYING:
                self._unknown(review, message)

    @staticmethod
    def _unknown(review, message):
        review.phase, review.result = Phase.FINISHED, None
        review.message = (
            f"{message}. The outcome is unknown: refresh to inspect; nothing is resent "
            "automatically"
        )

    def discard(self, review_id):
        with self._lock:
            review = self._get(review_id)
            if review.phase == Phase.APPLYING:
                raise ReviewUnavailable(
                    "An organization change that is being applied cannot be discarded"
                )
            review.phase = Phase.DISCARDED
            review.message = "Discarded"
            return self.status(review_id)

    def status(self, review_id):
        with self._lock:
            review = self._get(review_id)
            expires_in = None
            if review.phase == Phase.READY:
                expires_in = max(0.0, self._ttl - (self._clock() - review.ready_at))
            return ReviewStatus(
                review.review_id,
                review.phase,
                review.request,
                review.snapshot,
                review.result,
                review.message,
                expires_in,
                review.existing_collection_ids,
            )

    def clear(self):
        with self._lock:
            self._reviews.clear()


def collection_summary(record):
    """Project one collection without thumbnails, owner IDs or signed URLs."""
    name = record.get("name")
    summary = {"collection_id": record["id"], "name": name if isinstance(name, str) else ""}
    for key, field in (
        ("assetCount", "asset_count"),
        ("modelCount", "model_count"),
        ("updatedAt", "updated_at"),
    ):
        value = record.get(key)
        valid = isinstance(value, str) if key == "updatedAt" else isinstance(value, int | float)
        summary[field] = value if valid and not isinstance(value, bool) else None
    return summary


def _member(collection_id, collection_ids):
    if collection_id is None or collection_ids is None:
        return None
    return collection_id in collection_ids


def review_payload(status):
    """JSON-safe status for both surfaces; no URLs, owner IDs or service text."""
    request, snapshot, result = status.request, status.snapshot, status.result
    assets = []
    if snapshot is not None:
        changes = {change.asset_id: change for change in snapshot.changes}
        for asset in snapshot.assets:
            change = changes[asset.asset_id]
            membership = None
            if change.membership:
                removing = request.operation == Operation.REMOVE_FROM_COLLECTION
                membership = "remove" if removing else "add"
            assets.append(
                {
                    "asset_id": asset.asset_id,
                    "name": asset.name,
                    "tags": list(asset.tags),
                    "in_collection": _member(request.collection_id, asset.collection_ids),
                    "change": {
                        "membership": membership,
                        "add_tags": list(change.add_tags),
                        "remove_tags": list(change.remove_tags),
                    },
                }
            )
    collection_name = request.collection_name
    if snapshot is not None and snapshot.collection_name is not None:
        collection_name = snapshot.collection_name
    payload = {
        "review_id": status.review_id,
        "phase": status.phase.value,
        "operation": request.operation.value,
        "project_id": request.scope.project_id,
        "asset_ids": list(request.asset_ids),
        "collection_id": request.collection_id,
        "collection_name": collection_name,
        "add_tags": list(request.add_tags),
        "remove_tags": list(request.remove_tags),
        "assets": assets,
        "missing_asset_ids": list(snapshot.missing) if snapshot is not None else [],
        "existing_collection_ids": list(
            status.existing_collection_ids
            or (snapshot.existing_collection_ids if snapshot is not None else ())
        ),
        "request_count": snapshot.request_count if snapshot is not None else None,
        "expires_in": None if status.expires_in is None else round(status.expires_in),
        "message": status.message,
        "notice": NOTICE,
        "result": None,
    }
    if result is not None:
        payload["result"] = {
            "state": result.state.value,
            "requests_sent": result.requests_sent,
            "collection_id": result.collection_id,
            "created_collection_id": result.created_collection_id,
            "create_outcome": result.create_outcome.value if result.create_outcome else None,
            "create_status": result.create_status,
            "outcomes": [
                {
                    "asset_id": outcome.asset_id,
                    "state": outcome.state.value,
                    "status": outcome.status,
                    "tags": None if outcome.tags is None else list(outcome.tags),
                    # Membership in the target collection, including one just created.
                    "in_collection": _member(result.collection_id, outcome.collection_ids),
                }
                for outcome in result.outcomes
            ],
        }
    return payload
