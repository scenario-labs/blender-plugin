# Scoped upload metadata commands

The shared [SDK adapter](../scenario/core/api/sdk_adapter.py) exposes the
multipart upload metadata lifecycle through the packaged **scenario-sdk 2.1.0**.
These commands do not read files, transfer bytes, persist signed URLs, start a
background worker or connect the prototype UI/MCP. They are a foundation for
[#64](https://github.com/scenario-labs/blender-plugin/issues/64) and
[#65](https://github.com/scenario-labs/blender-plugin/issues/65).

| Command | Public SDK method | Behavior |
| --- | --- | --- |
| `create_upload(...)` | `uploads.with_raw_response.create` | POST multipart metadata once; returns the unwrapped `upload` record |
| `upload(identifier)` | `uploads.with_raw_response.retrieve` | GET a known upload in the selected project |
| `complete_upload(identifier)` | `uploads.with_raw_response.trigger_action(action="complete")` | Explicitly request completion once; return the actual reported processing state |

The adapter's selected credentials, HTTPS API endpoint and immutable project
apply to every command. Callers cannot inject a different project or arbitrary
SDK extension parameters through upload options. Online permission is checked
before each request; closed clients reject commands. The SDK has retries disabled
and redirects disabled, including for reads and completion acknowledgements.
A selected local account/team identity is not itself proof of server permissions.

## Inputs and responses

Initialization accepts the SDK's multipart kinds (`3d`, `asset`, `audio`,
`avatar`, `image`, `model`, `text`, `video`), a file basename, a bare MIME type,
an integer byte count and a positive integer part count. Zero bytes are allowed
as metadata; this does not claim the service accepts empty media. These local
checks do not invent service size/part limits or a chunking policy. The caller
must bind this metadata to its actual file before future byte transfer.

Optional asset settings use the SDK's `collection_ids`, `parent_id` and `hide`
names; the SDK serializes their documented camel-case wire aliases. They are
copied and validated before dispatch. Model uploads reject asset options,
matching the selected SDK's contract. URL ingestion and model-provider import
shortcuts are outside this multipart-only interface.

Upload and asset-option identifiers follow a local maximum of 256 characters
and reject path separators, URL metacharacters, whitespace and control characters.
Every response must contain an `upload` object with a valid ID and a nonempty
string status. Retrieval/completion require the returned ID to match the requested
one. The adapter retains unknown fields and statuses instead of manufacturing a
terminal result. Transfer instructions are preserved as metadata; they are **not
a validated or authorized storage transfer plan**. Do not log raw records: parts
may contain signed URLs and other sensitive response details.

## Completion and uncertain responses

The SDK 2.1.0 generated action parameter is `Literal["complete"]`; its docstring
says `"upload-complete"`. The adapter uses the generated literal already covered
by the dependency contracts. Actual service acceptance remains unverified; do not
silently substitute another action or invent an abort endpoint.

Only an explicit caller action can initialize or finalize an upload. The caller
must first establish that all its parts transferred successfully before calling
`complete_upload`. This low-level adapter cannot establish that from metadata.
A `validating` acknowledgement stays `validating`; even `complete` must not be
silently interpreted as an imported asset. Preserve the returned `entityId`,
`jobId`, actual status and future fields for the higher-level lifecycle.

A timeout, HTTP failure or invalid receipt after a mutation may leave an upload
created or completion accepted remotely. The adapter raises a redacted error and
makes no second request. It does not automatically create another upload, repeat
completion or poll. A higher-level owner must persist request/file/scope identity,
retain known upload IDs, distinguish uncertain mutation from transfer failure,
and reconcile through explicit reads. An unknown initialization ID remains
uncertain; do not attach a guessed upload or automatically recreate it.

## Remaining integration and verification

A signed PUT primitive is available as described below. File staging/part planning,
expiry policy, upload orchestration/completion reconciliation, server
cleanup and UI/MCP wiring remain separate work. Storage requests must check destination/online policy and never forward
Scenario Authorization. No upload-abort method was established in this SDK.

Offline contracts exercise the actual SDK through MockTransport, including
scoping, field aliases, one-attempt failures, response identity, future processing
states, invalid inputs and ambient credential isolation. Installed-ZIP tests use
the bundled SDK with synthetic responses. These checks do not establish live
upload acceptance, OAuth transport or successful file import. Live checks require
their own authorized project and applicable budget.


## Signed part byte transfer

[`PartUploader`](../scenario/core/jobs/upload_transfers.py) performs one storage
PUT attempt for a supplied immutable `bytes` snapshot. SDK upload initialization,
retrieval and completion remain in the shared adapter. The pinned SDK exposes
numbered part URLs and expiration metadata; it does not transfer these bytes.
The primitive introduces no raw Scenario API endpoint or SDK fallback.

The caller must persist the upload identity, original scope, source/part digest
and transfer claim before calling it. It must bind the chosen URL and part number
to that SDK upload plan, check expiration, and choose an explicit part-size policy.
There is no implicit trusted-host list: the caller supplies the same exact HTTPS
`StoragePolicy` used by downloads. Policy hosts must come from reviewed configuration,
not from an incoming URL. No method initializes or finalizes an upload here.

Inputs require a positive part number, a nonempty immutable byte snapshot within
the policy's byte limit, a bare MIME type, and a SHA256 matching the saved part
identity. Invalid or changed bytes fail before connecting. Large files must be
staged and split by the application; this primitive never reads the user's source
path or assembles a whole file in memory. Empty media needs a separately verified
service contract rather than an invented zero-part upload.

The transport uses verified TLS with bundled certificate authorities and sends
only PUT, Content-Type, Content-Length and Connection: close (plus HTTP's Host).
It has no Scenario credentials, cookies, ambient proxy/certificate settings,
redirect handling, URL logging or automatic retry. Body writes are at most 64 KiB;
permission and elapsed-time budget are checked between them and before reading
the response. Blocking DNS/TLS/socket calls retain the existing transfer timeout
limitations. Revocation cannot retract bytes already sent.

HTTP 200, 201 or 204 yields a URL-free `UploadedPart(number, size, sha256)` receipt.
This acknowledges this PUT only; it does not establish remote digest validation,
all-parts completion or successful asset import. Response bodies and ETags are
neither read nor persisted. The selected SDK completion method does not take ETags.

Failures before the first possible HTTP write raise sanitized `TransferError`.
After that boundary, transport errors and non-success HTTP statuses raise
`UploadUncertain`: storage may have accepted bytes. There is no retry or automatic
completion. The caller must preserve the durable claim and reconcile using the
known upload identity. Control exceptions propagate after cleanup and likewise
must leave the caller's persisted claim available for recovery. Ordinary cleanup
errors do not replace an acknowledged receipt with a failure that could invite
replay. These are offline transport contracts, not live upload acceptance.


## Durable upload claims

[`UploadStore`](../scenario/core/jobs/upload_store.py) records immutable source
metadata, whole-file and per-part SHA256 identities, original account/project
scope and Blender origin in a separate versioned SQLite database. It does not
read source files, run workers or call the network. The application must stage
and hash its actual source before creating the intent, then verify each part
against that identity before sending it. Signed URLs and credentials have no
fields in this record. Local chunking limits are not service acceptance claims.

Initialization, each part, and finalization require a committed claim before the
caller performs the corresponding mutation. Revisions and immediate SQLite
transactions reject stale or competing claims across connections. A part receipt
must match the claimed number, exact size and saved digest; receipts form an
ordered prefix. Finalization requires every receipt. Only an authoritative
imported observation can attach an asset ID.

Reopening preserves in-flight states verbatim. An interrupted initialization
without a known remote ID remains uncertain; it cannot be reset or recreated.
A part claimed without a receipt cannot be claimed again, including after a
restart. Uncertain finalization cannot be retried. Explicit SDK reads of a known
upload may reconcile processing, imported or failed observations without sending
bytes again. The selected SDK has no per-part receipt or abort API; pending
remote status alone cannot prove an interrupted part was rejected. No automatic
retry or cleanup endpoint is invented here.

The store validates source identity, state invariants, scope and revision when
reading. Missing/corrupt records, foreign databases, future versions and failed
writes raise errors and preserve evidence rather than resetting storage. Failed
receipt persistence leaves the earlier claim in place. New database files and
directories use private permissions where supported. The application owns the
storage directory under Blender's extension user path and must prevent its
replacement while in use. This database is separate from the job database;
there is no migration or active prototype integration in this component.
