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

Signed byte transfer, expiry policy, file identity checks, durable upload state,
completion/restart reconciliation, server cleanup and UI/MCP wiring remain separate
work. Storage requests must check destination/online policy and never forward
Scenario Authorization. No upload-abort method was established in this SDK.

Offline contracts exercise the actual SDK through MockTransport, including
scoping, field aliases, one-attempt failures, response identity, future processing
states, invalid inputs and ambient credential isolation. Installed-ZIP tests use
the bundled SDK with synthetic responses. These checks do not establish live
upload acceptance, OAuth transport or successful file import. Live checks require
their own authorized project and applicable budget.
