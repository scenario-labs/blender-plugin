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
[adapter](../scenario/core/api/sdk_adapter.py): `assets.with_raw_response.retrieve`
for one asset and `assets.with_raw_response.get_bulk` for several, in chunks of
100 identities (the SDK documents a 200-identity limit). Both carry the selected
project, use the client's `max_retries=0` and check online access before each
request. One batch reads its metadata once. The published wheel's
`types/asset_retrieve_response.py` documents the optional `thumbnail` and `preview`
objects, each with an `assetId` and a signed `url`; see the
[asset retrieval contract](https://docs.scenario.com/api/python/resources/assets/methods/retrieve).
The record must match the saved asset identity and MIME type. Signed URLs stay in
memory and are never written, logged or returned in errors.

Bytes use the existing [signed result transfer](RESULT_TRANSFERS.md) with the same
configured storage hosts, redirect rules and online-access predicate, and smaller
caps: 8 MiB for a still and 64 MiB for a clip. The content, not the URL or a
declared type, must be PNG, JPEG or WebP for a still and MP4 or WebM for a clip.
A host outside the policy, an oversized or unsupported file, or a metadata
mismatch fails that rendition with a sanitized reason and caches nothing.

Server previews are bound to the saved asset identity and receipt digest. Their
bytes are produced by the service, not derived from the saved file, so they are
not a content attestation of the result.

## Polling window

Server previews can appear minutes after a result is saved. The scheduler polls
missing ones on the preview lane with backoff delays of 5, 10, 20, 40 and then
60 seconds. The window lasts 300 seconds from the first online poll; the last poll
lands at its end. If no preview appeared, the cache records a `missing` marker for
that receipt and later requests show it without polling again. An explicit
`retry` clears the marker and opens a new window.

Without online access, renditions report `offline` and are checked every five
seconds without consuming the window. Metadata read failures stay `pending` with
the same backoff and become `failed` at the window's end, as do repeated lane task
failures. No result state is persisted in `jobs.sqlite3`: the window starts in
memory, and the `missing` marker is what prevents a new window after a restart.

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
directory. Entries live in `v1/<scope digest>/<key digest>/`; the scope digest
matches the saved result partition and the key also binds the request, asset,
MIME type and receipt digest and size. Another credential, project, request or
byte content therefore never shares an entry. Stills and clips have a data file
and a JSON sidecar holding digests, sizes, dimensions and the server preview
asset ID, never a URL, credential or prompt. Envelopes and `missing` markers are
sidecars only.

Reads accept only a regular, nonsymlink file whose size, digest and signature
match its sidecar; anything else is a cache miss. Publication never replaces a
valid entry. At most every ten minutes the lane removes abandoned work
directories older than a day and evicts the least recently used entries beyond
512 MiB, keeping entries used in the last minute. A ready status can therefore
outlive its file; an explicit retry reads or fetches it again. The cache is safe
to delete.

## Lane and ownership

`JobWorkers` owns one dedicated `ScenarioPreview` thread with its own bounded
queue of eight tasks and per-task cancellation. Preview polling, copies and
downloads therefore never occupy the job workers used by remote refresh, result
downloads and submissions, and never use the single local media slot.
Deactivation cancels queued previews and signals the running one; shutdown joins
the lane with the other workers. A transfer already in flight finishes or times
out under the storage policy.

`ResultPreviewScheduler` runs on its owner thread, normally Blender's main
thread, and performs no I/O. `request`, `retry`, `status`, `decode_requests`,
`finish_decode` and `discard_decode` are its interface; status snapshots are
immutable and safe to read while drawing. It sends at most one batch of up to 32
assets at a time.

`JobSession(preview_root=...)` exposes it as `result_previews` while the session
is active. The session's existing maintenance timer, and `reap_retired` in
headless loops, call `service_previews`. Deactivation closes the scheduler;
shutdown removes remaining private copies after the workers stop. See the
[job context contract](BLENDER_JOB_CONTEXT.md#saved-result-preview-ownership).

## Boundaries

These are offline contracts with synthetic SDK and storage fixtures. Which asset
kinds receive server thumbnails or previews, their sizes, signed URL lifetime and
hosts, and their timing after a job succeeds are not established by live
evidence. Blender-side decoding, the user interface, MCP parity and native
desktop acceptance remain open under #189, #65 and #66.
