# Saved-result previews

[`result_previews`](../scenario/core/jobs/result_previews.py) and
[`preview_scheduler`](../scenario/core/jobs/preview_scheduler.py) prepare small
previews of downloaded saved results for the shared runtime. They are bpy-free.
Previews are read-only: they never submit, spend, apply, resolve a scene origin or
write the job store. This runtime layer has no user interface or local MCP tool
yet. Blender-side decoding, display, playback and waveform drawing are follow-up
work under [#189](https://github.com/scenario-labs/blender-plugin/issues/189) and
[#66](https://github.com/scenario-labs/blender-plugin/issues/66).

## Sources by result type

Only results with a saved download receipt are previewed, in the states `ready`,
`applying`, `apply_failed` and `applied`. An interrupted application is allowed
because previews never touch the scene. The saved manifest's MIME type selects
the source:

| Saved result | Still | Other renditions |
| --- | --- | --- |
| PNG, JPEG, WebP and OpenEXR images | Local decode request for the verified result | None |
| Video | Server `thumbnail` | Server `preview` clip, only when requested |
| 3D models, except MTL material libraries | Server `thumbnail` | Server `preview` turntable clip, only when requested |
| WAV, MP3, OGG, FLAC, M4A and AAC audio | Server `thumbnail` when offered | Local RMS envelope from decoded samples |
| Anything else | Unsupported | None |

Image previews use the verified local bytes, not CDN transformation parameters,
which are undocumented CDN behavior.

## Server stills and clips

Metadata uses the selected SDK 2.2.0 through the shared
[adapter](../scenario/core/api/sdk_adapter.py):
`assets.with_raw_response.get_bulk` for every batch, a single asset included, in
chunks of 100 identities (the SDK documents a 200-identity limit). It carries the
selected project, uses the client's `max_retries=0` and checks online access
before each request. One batch reads its metadata once. The published wheel's
`types/asset_get_bulk_response.py`, like `types/asset_retrieve_response.py`,
documents the optional `thumbnail` and `preview` objects, each with an `assetId`
and a signed `url`; see the
[asset retrieval contract](https://docs.scenario.com/api/python/resources/assets/methods/retrieve).
The record must match the saved asset identity and MIME type. Signed URLs stay in
memory and are never written, logged or returned in errors.

Using one method for every batch size gives an absent asset one meaning. An
asset the server omits, for example one deleted after the job, is treated like
a preview that has not appeared yet: it is polled within the window, then marked
`missing`. A failed or malformed response, including an unrequested record,
remains a read failure, described under the polling window.

Bytes use the existing [signed result transfer](RESULT_TRANSFERS.md) with the same
configured storage hosts, redirect rules and online-access predicate, and smaller
caps: 8 MiB for a still and 64 MiB for a clip. The content, not the URL or a
declared type, must be PNG, JPEG or WebP for a still and MP4 or WebM for a clip.
Blender will decode stills on its main thread, so the byte cap alone does not
bound decode memory. A still must also declare at most 4096 pixels per side in
its PNG `IHDR` chunk, JPEG start-of-frame segment or WebP `VP8`, `VP8L` or
`VP8X` header; the checked dimensions are stored in its sidecar. A host outside
the policy, an oversized, unsupported or dimensionless file, or a metadata
mismatch fails that rendition with a sanitized reason and caches nothing.

Server previews are bound to the saved asset identity and receipt digest. Their
bytes are produced by the service, not derived from the saved file, so they are
not a content attestation of the result.

## Polling window

Server previews can appear minutes after a result is saved. The scheduler polls
missing ones on the preview lane with backoff delays of 5, 10, 20, 40 and then
60 seconds. The window measures 300 seconds of online polling: it opens at the
first online poll and the last poll lands at its end. If no preview appeared,
the cache records a `missing` marker for that receipt and later requests show it
without polling again. An explicit `retry` clears the marker and opens a new
window. Requesting a rendition the result did not have yet, such as a clip after
its still, also opens a new window and restarts the backoff for that result, so
the clip is not judged by a window the still already used. Renditions still
polling share the new window. A retry received while that result's batch is on
the lane is recorded and applied when the batch returns, so the late outcome
cannot undo it.

Without online access, renditions report `offline` and are checked every five
seconds. An offline poll pauses the window, keeping the time already used since
it opened, and the next online poll resumes it instead of starting a new one.
Metadata read failures stay `pending` with the same backoff and become `failed`
at the window's end, as do repeated lane task failures. No result state is
persisted in `jobs.sqlite3`: the window starts in memory, and the `missing`
marker is what prevents a new window after a restart.

The backoff applies only to `pending` and `offline` renditions. A rendition
that was not sent with a batch, because the decode limit below held it back or
because it was requested while the batch ran, stays `queued` and goes with the
next pump.

## Local images and audio

For an image still or an audio envelope, the lane copies the saved file into a
new private `work/preview-*` directory of the cache, rehashing it against its
receipt while copying, and checks the copy's container signature. The copy has
a canonical name, never the provider's file name. Sources are capped at 128 MiB
for images and 256 MiB for audio. The scheduler keeps at most four such decode
requests outstanding and fails one after 120 seconds without a result.

Blender decodes the request later on its main thread. For a still it writes a
PNG of at most 256 pixels per side to the request's `output`. Publication checks
the PNG signature, header checksum, dimensions and a 4 MiB size limit before
caching it. For audio,
[`EnvelopeBuilder`](../scenario/core/audio_waveform.py) reduces interleaved decoded
float samples to 10 ms blocks and then to at most 1024 RMS and peak bins. It
accepts up to 600 seconds, eight channels and 192 kHz, clamps samples to full
scale, rejects non-finite values and never reads files. Every finished or
discarded request removes its private copy.

## Cache

The runtime passes `cache/result-previews` under Blender's extension user
directory. If that directory cannot be created, the session still runs jobs and
`result_previews` reports that previews are not configured. Entries live in
`v1/<scope digest>/<key digest>/`; the scope digest matches the saved result
partition and the key also binds the request, asset, MIME type and receipt
digest and size. Another credential, project, request or byte content therefore
never shares an entry. Stills and clips have a data file and a JSON sidecar
holding digests, sizes, dimensions and the server preview asset ID, never a URL,
credential or prompt. Envelopes and `missing` markers are sidecars only.

Like saved results, the paths the cache returns, including decode requests,
use the canonical spelling of its root: on Windows, the extended-length `\\?\`
namespace. Compare them with that canonical root, not with the configured one.
Work directories are built on that root and take only their name from
`mkdtemp`, which normalizes the path it returns on Python 3.12 and later.

Reads accept only a regular, nonsymlink file whose size, digest and signature
match its sidecar; anything else is a cache miss. Publication never replaces a
valid entry. At most every ten minutes the lane removes abandoned work
directories older than a day and evicts the least recently used entries beyond
512 MiB, keeping entries used in the last minute. A ready status can therefore
outlive its file; an explicit retry reads or fetches it again. The cache is safe
to delete, even while Blender runs: each lane command recreates the root as a
private directory when its parent still exists.

## Lane and ownership

`JobWorkers` owns one dedicated `ScenarioPreview` thread with its own bounded
queue of eight tasks and per-task cancellation. Preview polling, copies and
downloads therefore never occupy the job workers used by remote refresh, result
downloads and submissions, and never use the single local media slot.
Deactivation cancels queued previews and signals the running one. A storage
transfer stops at its next permission check once signaled, before publishing
anything; an SDK metadata read cannot be interrupted and finishes or times out
under the client policy. `JobWorkers.previews_idle` reports when no preview
command is queued or running. Shutdown joins the lane with the other workers.

`ResultPreviewScheduler` runs on its owner thread, normally Blender's main
thread, and performs no network I/O or preview cache work. `request` reads saved
receipts from the local job store, and `release` removes leftover private copies
after the lane stops. `request`, `retry`, `status`, `decode_requests`,
`finish_decode` and `discard_decode` are its interface; status snapshots are
immutable and safe to read while drawing. It sends at most one batch of up to 32
assets at a time.

`JobSession(preview_root=...)` exposes it as `result_previews` while the session
is active. The session's existing maintenance timer, and `reap_retired` in
headless loops, call `service_previews`. Deactivation closes the scheduler. The
timer shuts a retired session down only once its preview lane is idle, so an
in-flight preview read never blocks Blender's main thread; the session stays
registered until then. Shutdown removes remaining private copies after the
workers stop. Extension disable or exit still joins any running preview command.
See the [job context contract](BLENDER_JOB_CONTEXT.md#saved-result-preview-ownership).

## Boundaries

These are offline contracts with synthetic SDK and storage fixtures. Which asset
kinds receive server thumbnails or previews, their sizes and dimensions, signed
URL lifetime and hosts, their timing after a job succeeds, and how `get_bulk`
reports a deleted asset are not established by live evidence. Blender-side decoding, the user interface, MCP parity and native
desktop acceptance remain open under #189, #65 and #66.
